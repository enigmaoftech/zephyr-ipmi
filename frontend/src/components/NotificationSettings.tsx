import { Button, Group, Paper, Select, Stack, Switch, Text, TextInput, Title } from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconPlus, IconSend, IconTrash } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { createChannel, deleteChannel, fetchChannels, testChannel } from '../services/api';

const channelTypes = [
  { value: 'slack', label: 'Slack' },
  { value: 'teams', label: 'Microsoft Teams' },
  { value: 'discord', label: 'Discord' },
  { value: 'telegram', label: 'Telegram' }
];

const triggerTypes = [
  { value: 'connectivity', label: 'Server connectivity lost' },
  { value: 'intrusion', label: 'Chassis intrusion detected' },
  { value: 'memory_error', label: 'Memory error detected' },
  { value: 'power_failure', label: 'Power supply failure' },
  { value: 'temperature_critical', label: 'Critical temperature exceeded' }
];

interface NotificationSettingsProps {
  onUpdate: () => void;
}

export default function NotificationSettings({ onUpdate }: NotificationSettingsProps) {
  const [channels, setChannels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, string>>({});

  const form = useForm({
    initialValues: {
      name: '',
      type: 'slack',
      endpoint: '',
      chat_id: '',
      enabled: true
    },
    validate: {
      name: (value) => (value.trim().length ? null : 'Alert name required'),
      endpoint: (value) => (value.trim().length ? null : 'Webhook URL or token required')
    }
  });

  const loadChannels = async () => {
    setLoading(true);
    try {
      const data = await fetchChannels();
      setChannels(data);
    } catch (err: any) {
      setError('Failed to load notification channels');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadChannels();
  }, []);

  const handleSubmit = form.onSubmit(async (values) => {
    setError(null);
    try {
      const payload: any = {
        name: values.name,
        type: values.type,
        endpoint: values.endpoint,
        enabled: values.enabled
      };
      if (values.type === 'telegram' && values.chat_id) {
        payload.chat_id = values.chat_id;
      }
      await createChannel(payload);
      form.reset();
      await loadChannels();
      onUpdate();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to create channel';
      setError(detail);
    }
  });

  const handleDelete = async (channelId: number) => {
    try {
      await deleteChannel(channelId);
      await loadChannels();
      onUpdate();
    } catch (err: any) {
      setError('Failed to delete channel');
    }
  };

  const handleTest = async (channelId: number) => {
    setTestingId(channelId);
    setTestResults((prev) => ({ ...prev, [channelId]: '' }));
    setError(null);
    try {
      const result = await testChannel(channelId);
      setTestResults((prev) => ({ ...prev, [channelId]: `✓ ${result.message}` }));
      setTimeout(() => {
        setTestResults((prev) => {
          const newResults = { ...prev };
          delete newResults[channelId];
          return newResults;
        });
      }, 5000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Test failed';
      setTestResults((prev) => ({ ...prev, [channelId]: `✗ ${detail}` }));
      setTimeout(() => {
        setTestResults((prev) => {
          const newResults = { ...prev };
          delete newResults[channelId];
          return newResults;
        });
      }, 5000);
    } finally {
      setTestingId(null);
    }
  };

  return (
    <Stack gap="xl">
      <div>
        <Title order={3}>Notification Settings</Title>
        <Text c="dimmed" size="sm">
          Configure alert channels for server events (Teams, Slack, Discord, Telegram)
        </Text>
      </div>

      <Paper shadow="sm" radius="md" p="xl" withBorder>
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={4}>Add Notification Channel</Title>
            <TextInput
              label="Alert name"
              placeholder="Production Alerts"
              required
              {...form.getInputProps('name')}
            />
            <Select
              label="Channel type"
              data={channelTypes}
              required
              {...form.getInputProps('type')}
            />
            <TextInput
              label={form.values.type === 'telegram' ? 'Bot token' : 'Webhook URL'}
              placeholder={form.values.type === 'telegram' ? '123456:ABC-DEF...' : 'https://hooks.slack.com/services/...'}
              required
              {...form.getInputProps('endpoint')}
            />
            {form.values.type === 'telegram' && (
              <TextInput
                label="Chat ID"
                placeholder="@channel or chat ID"
                {...form.getInputProps('chat_id')}
              />
            )}
            <Switch label="Enabled" {...form.getInputProps('enabled', { type: 'checkbox' })} />
            {error && (
              <Text c="red" size="sm">
                {error}
              </Text>
            )}
            <Group justify="flex-end">
              <Button type="submit">Add channel</Button>
            </Group>
          </Stack>
        </form>
      </Paper>

      {channels.length > 0 && (
        <div>
          <Title order={4}>Configured Channels</Title>
          <Stack gap="sm" mt="md">
            {channels.map((channel) => (
              <Paper key={channel.id} p="md" withBorder radius="md">
                <Stack gap="xs">
                  <Group justify="space-between">
                    <div>
                      <Text fw={500}>{channel.name}</Text>
                      <Text size="sm" c="dimmed">
                        {channel.type.toUpperCase()} • {channel.enabled ? 'Enabled' : 'Disabled'}
                      </Text>
                    </div>
                    <Group gap="xs">
                      {channel.enabled && (
                        <Button
                          variant="light"
                          size="xs"
                          leftSection={<IconSend size={14} />}
                          loading={testingId === channel.id}
                          onClick={() => handleTest(channel.id)}
                        >
                          Test
                        </Button>
                      )}
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<IconTrash size={14} />}
                        onClick={() => handleDelete(channel.id)}
                      >
                        Remove
                      </Button>
                    </Group>
                  </Group>
                  {testResults[channel.id] && (
                    <Text size="sm" c={testResults[channel.id].startsWith('✓') ? 'green' : 'red'}>
                      {testResults[channel.id]}
                    </Text>
                  )}
                </Stack>
              </Paper>
            ))}
          </Stack>
        </div>
      )}
    </Stack>
  );
}
