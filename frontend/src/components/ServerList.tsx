import { Badge, Button, Card, Group, Stack, Text, Title, Alert as MantineAlert } from '@mantine/core';
import { IconAlertCircle, IconCheck, IconCircleX, IconEdit, IconTestPipe, IconTrash, IconX } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { clearServerAlert, getServerAlerts, testServerConnection } from '../services/api';
import type { ActiveAlert, Server } from '../types/api';

interface ServerListProps {
  servers: Server[];
  onEdit: (server: Server) => void;
  onDelete: (serverId: number) => void;
}

export default function ServerList({ servers, onEdit, onDelete }: ServerListProps) {
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, { status: string; message: string }>>({});
  const [serverAlerts, setServerAlerts] = useState<Record<number, ActiveAlert[]>>({});
  const [loadingAlerts, setLoadingAlerts] = useState<Record<number, boolean>>({});

  useEffect(() => {
    // Load alerts for all servers
    const loadAlerts = async () => {
      for (const server of servers) {
        try {
          const alerts = await getServerAlerts(server.id);
          setServerAlerts((prev) => ({ ...prev, [server.id]: alerts }));
        } catch (err) {
          console.error(`Failed to load alerts for server ${server.id}:`, err);
        }
      }
    };
    void loadAlerts();

    // Refresh alerts every 30 seconds
    const interval = setInterval(() => {
      void loadAlerts();
    }, 30000);

    return () => clearInterval(interval);
  }, [servers]);

  const handleTest = async (serverId: number) => {
    setTestingId(serverId);
    setTestResults((prev) => ({ ...prev, [serverId]: { status: 'testing', message: 'Testing connection...' } }));
    try {
      const result = await testServerConnection(serverId);
      setTestResults((prev) => ({ ...prev, [serverId]: result }));
      setTimeout(() => {
        setTestResults((prev) => {
          const newResults = { ...prev };
          delete newResults[serverId];
          return newResults;
        });
      }, 5000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Test failed';
      setTestResults((prev) => ({ ...prev, [serverId]: { status: 'error', message: detail } }));
      setTimeout(() => {
        setTestResults((prev) => {
          const newResults = { ...prev };
          delete newResults[serverId];
          return newResults;
        });
      }, 5000);
    } finally {
      setTestingId(null);
    }
  };

  const handleClearAlert = async (serverId: number, alertType: string) => {
    setLoadingAlerts((prev) => ({ ...prev, [serverId]: true }));
    try {
      await clearServerAlert(serverId, alertType);
      // Reload alerts for this server
      const alerts = await getServerAlerts(serverId);
      setServerAlerts((prev) => ({ ...prev, [serverId]: alerts }));
    } catch (err) {
      console.error(`Failed to clear alert for server ${serverId}:`, err);
    } finally {
      setLoadingAlerts((prev) => ({ ...prev, [serverId]: false }));
    }
  };

  const getAlertTypeLabel = (alertType: string): string => {
    return alertType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  if (servers.length === 0) {
    return (
      <Card withBorder shadow="sm" radius="md">
        <Text c="dimmed">No servers configured yet. Add one to get started.</Text>
      </Card>
    );
  }

  return (
    <Stack gap="md">
      {servers.map((server) => {
        const testResult = testResults[server.id];
        return (
          <Card key={server.id} withBorder shadow="sm" radius="md">
            <Stack gap="xs">
              <Group justify="space-between">
                <Title order={4}>{server.name}</Title>
                <Group gap="xs">
                  <Badge>{server.vendor.toUpperCase()}</Badge>
                  <Button
                    variant="light"
                    size="xs"
                    leftSection={<IconTestPipe size={14} />}
                    loading={testingId === server.id}
                    onClick={() => handleTest(server.id)}
                  >
                    Test
                  </Button>
                  <Button
                    variant="light"
                    size="xs"
                    leftSection={<IconEdit size={14} />}
                    onClick={() => onEdit(server)}
                  >
                    Edit
                  </Button>
                  <Button
                    variant="light"
                    color="red"
                    size="xs"
                    leftSection={<IconTrash size={14} />}
                    onClick={() => onDelete(server.id)}
                  >
                    Delete
                  </Button>
                </Group>
              </Group>
              <Text size="sm" c="dimmed">
                BMC: {server.bmc_host}:{server.bmc_port} • Poll every {Math.round(server.poll_interval_seconds / 60)} min
              </Text>
              {server.metadata && (server.metadata as { room?: string }).room && (
                <Text size="sm" c="dimmed" style={{ whiteSpace: 'pre-wrap' }}>
                  Notes: {(server.metadata as { room: string }).room}
                </Text>
              )}
              {testResult && (
                <Group gap="xs">
                  {testResult.status === 'success' ? (
                    <IconCheck size={16} color="green" />
                  ) : (
                    <IconX size={16} color="red" />
                  )}
                  <Text size="sm" c={testResult.status === 'success' ? 'green' : 'red'}>
                    {testResult.message}
                  </Text>
                </Group>
              )}
              {server.fan_defaults && server.fan_defaults.zones && (
                <Text size="sm" c="dimmed">
                  Fan zones: {server.fan_defaults.zones.length} configured
                </Text>
              )}
              {server.notification_channel_ids && server.notification_channel_ids.length > 0 && (
                <Text size="sm" c="dimmed">
                  Notifications: {server.notification_channel_ids.length} channel(s) configured
                </Text>
              )}
              {server.alert_config && Object.keys(server.alert_config).length > 0 && (
                <Group gap="xs">
                  <Text size="sm" c="dimmed">
                    Alerts enabled:
                  </Text>
                  {Object.entries(server.alert_config)
                    .filter(([, enabled]) => enabled)
                    .map(([alertType]) => (
                      <Badge key={alertType} size="xs" variant="light">
                        {alertType.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      </Badge>
                    ))}
                </Group>
              )}
              {server.fan_overrides.length > 0 && (
                <Text size="sm" c="dimmed">
                  Overrides: {server.fan_overrides.map((fan) => fan.fan_identifier).join(', ')}
                </Text>
              )}
              {serverAlerts[server.id] && serverAlerts[server.id].length > 0 && (
                <Stack gap="xs" mt="sm">
                  <Text size="sm" fw={600} c="red">
                    Active Alerts:
                  </Text>
                  {serverAlerts[server.id].map((alert) => (
                    <MantineAlert
                      key={alert.id}
                      icon={<IconAlertCircle size={16} />}
                      title={
                        <Group justify="space-between" align="center">
                          <Text fw={600}>{getAlertTypeLabel(alert.alert_type)}</Text>
                          <Button
                            variant="subtle"
                            color="red"
                            size="xs"
                            leftSection={<IconCircleX size={14} />}
                            loading={loadingAlerts[server.id]}
                            onClick={() => handleClearAlert(server.id, alert.alert_type)}
                          >
                            Clear
                          </Button>
                        </Group>
                      }
                      color="red"
                      variant="light"
                    >
                      <Text size="xs" c="dimmed" style={{ whiteSpace: 'pre-wrap' }}>
                        {alert.message}
                      </Text>
                      <Text size="xs" c="dimmed" mt={4}>
                        Triggered: {new Date(alert.first_triggered_at).toLocaleString()}
                      </Text>
                    </MantineAlert>
                  ))}
                </Stack>
              )}
            </Stack>
          </Card>
        );
      })}
    </Stack>
  );
}
