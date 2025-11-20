import { Button, Group, MultiSelect, NumberInput, Paper, PasswordInput, Select, Stack, Switch, Text, TextInput, Title } from '@mantine/core';
import { useForm } from '@mantine/form';
import { IconPlus, IconTrash } from '@tabler/icons-react';
import { useEffect, useState } from 'react';

import { createServer, fetchChannels, updateServer } from '../services/api';
import type { Server, ServerFanOverride } from '../types/api';

const vendorOptions = [
  { value: 'supermicro', label: 'Supermicro' },
  { value: 'dell', label: 'Dell' },
  { value: 'hp', label: 'HP' }
];

interface ServerFormProps {
  server?: Server | null;
  onCreated: (server: Server) => void;
  onCancel?: () => void;
}

interface TemperatureZone {
  tempThreshold: number;
  targetRpm: number;
}

interface FormValues {
  name: string;
  vendor: string;
  bmc_host: string;
  bmc_port: number;
  poll_interval_seconds: number;
  username: string;
  password: string;
  room_description: string;
  notification_channel_ids: number[];
  fan_zones: TemperatureZone[];
  fan_overrides: ServerFanOverride[];
  alert_config: {
    connectivity: boolean;
    memory_errors: boolean;
    power_failure: boolean;
    intrusion: boolean;
    voltage_issues: boolean;
    system_events: boolean;
    temperature_critical: boolean;
  };
  offline_alert_threshold_minutes: number;
}

export default function ServerForm({ server, onCreated, onCancel }: ServerFormProps) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [channels, setChannels] = useState<Array<{ value: string; label: string }>>([]);
  const [channelsLoading, setChannelsLoading] = useState(true);
  const isEditing = !!server;

  const getDefaultPort = (vendor: string) => {
    // All major IPMI vendors use port 623 by default
    return 623;
  };

  const getInitialValues = (): FormValues => {
    if (server) {
      // Populate form from server data
      const zones = server.fan_defaults?.zones || [
        { tempThreshold: 50, targetRpm: 1800 },
        { tempThreshold: 52, targetRpm: 3500 },
        { tempThreshold: 70, targetRpm: 5000 }
      ];
      return {
        name: server.name,
        vendor: server.vendor,
        bmc_host: server.bmc_host,
        bmc_port: server.bmc_port,
        poll_interval_seconds: server.poll_interval_seconds,
        username: '', // Cannot decrypt, user must re-enter
        password: '', // Cannot decrypt, user must re-enter
        room_description: server.metadata?.room || '',
        notification_channel_ids: server.notification_channel_ids || [],
        fan_zones: zones.map((z: any) => ({
          tempThreshold: z.temp_threshold || z.tempThreshold || 50,
          targetRpm: z.target_rpm || z.targetRpm || 1800
        })),
        fan_overrides: server.fan_overrides || [],
        alert_config: {
          connectivity: server.alert_config?.connectivity === true,
          memory_errors: server.alert_config?.memory_errors === true,
          power_failure: server.alert_config?.power_failure === true,
          intrusion: server.alert_config?.intrusion === true,
          voltage_issues: server.alert_config?.voltage_issues === true,
          system_events: server.alert_config?.system_events === true,
          temperature_critical: server.alert_config?.temperature_critical === true
        },
        offline_alert_threshold_minutes: server.offline_alert_threshold_minutes || 15
      };
    }
    return {
      name: '',
      vendor: 'supermicro',
      bmc_host: '',
      bmc_port: 623,
      poll_interval_seconds: 300,
      username: '',
      password: '',
      room_description: '',
      notification_channel_ids: [],
      fan_zones: [
        { tempThreshold: 50, targetRpm: 1800 },
        { tempThreshold: 52, targetRpm: 3500 },
        { tempThreshold: 70, targetRpm: 5000 }
      ],
      fan_overrides: [],
      alert_config: {
        connectivity: false,
        memory_errors: false,
        power_failure: false,
        intrusion: false,
        voltage_issues: false,
        system_events: false,
        temperature_critical: false
      },
      offline_alert_threshold_minutes: 15
    };
  };

  const form = useForm<FormValues>({
    initialValues: getInitialValues(),
    validate: {
      name: (value) => (value.trim().length ? null : 'Server name is required'),
      bmc_host: (value) => (value.trim().length ? null : 'BMC host/IP is required'),
      username: (value) => (isEditing ? null : (value.trim().length ? null : 'Username is required')),
      password: (value) => (isEditing ? null : (value.trim().length ? null : 'Password is required'))
    }
  });

  useEffect(() => {
    const loadChannels = async () => {
      try {
        const data = await fetchChannels();
        setChannels(
          data
            .filter((ch: any) => ch.enabled)
            .map((ch: any) => ({
              value: String(ch.id),
              label: `${ch.name} (${ch.type.toUpperCase()})`
            }))
        );
      } catch (err) {
        console.error('Failed to load notification channels:', err);
      } finally {
        setChannelsLoading(false);
      }
    };
    void loadChannels();
  }, []);

  useEffect(() => {
    if (server) {
      const values = getInitialValues();
      form.setValues(values);
    } else {
      form.reset();
      form.setFieldValue('fan_zones', [
        { tempThreshold: 50, targetRpm: 1800 },
        { tempThreshold: 52, targetRpm: 3500 },
        { tempThreshold: 70, targetRpm: 5000 }
      ]);
    }
  }, [server]);

  const addFanOverride = () => {
    form.insertListItem('fan_overrides', {
      fan_identifier: '',
      min_rpm: null,  // This is the RPM override
      max_rpm: null,
      lower_temp_c: null,
      upper_temp_c: null,
      profile: null
    });
  };

  const removeFanOverride = (index: number) => {
    form.removeListItem('fan_overrides', index);
  };

  const addZone = () => {
    if (form.values.fan_zones.length < 5) {
      const lastZone = form.values.fan_zones[form.values.fan_zones.length - 1];
      form.insertListItem('fan_zones', {
        tempThreshold: lastZone.tempThreshold + 10,
        targetRpm: lastZone.targetRpm + 500
      });
    }
  };

  const removeZone = (index: number) => {
    if (form.values.fan_zones.length > 1) {
      form.removeListItem('fan_zones', index);
    }
  };

  const getZoneColor = (index: number) => {
    const colors = [
      'var(--mantine-color-blue-0)',
      'var(--mantine-color-yellow-0)',
      'var(--mantine-color-orange-0)',
      'var(--mantine-color-red-0)',
      'var(--mantine-color-red-1)'
    ];
    return colors[Math.min(index, colors.length - 1)];
  };

  const getZoneLabel = (index: number, total: number) => {
    if (index === 0) return 'Zone 1: Low Temperature (Quiet Mode)';
    if (index === total - 1) return `Zone ${index + 1}: High Temperature (Performance Mode)`;
    return `Zone ${index + 1}: Medium Temperature`;
  };

  const getZoneDescription = (index: number, total: number) => {
    if (index === 0) {
      return 'When CPU temp is below this threshold, fans run at the quiet RPM setting.';
    }
    if (index === total - 1) {
      return `When CPU temp exceeds ${form.values.fan_zones[index - 1]?.tempThreshold || 'previous'}°C, fans run at high RPM. Set RPM to 0 for full speed.`;
    }
    return `When CPU temp is between ${form.values.fan_zones[index - 1]?.tempThreshold || 'previous'}°C and this threshold, fans run at this RPM.`;
  };

  const handleSubmit = form.onSubmit(async (values) => {
    setError(null);
    setLoading(true);

    const payload: any = {
      name: values.name,
      vendor: values.vendor,
      bmc_host: values.bmc_host,
      bmc_port: values.bmc_port,
      poll_interval_seconds: values.poll_interval_seconds,
      metadata: values.room_description.trim()
        ? {
            room: values.room_description.trim()
          }
        : {},
      fan_defaults: {
        zones: values.fan_zones.map((zone, index) => ({
          temp_threshold: zone.tempThreshold,
          target_rpm: zone.targetRpm,
          zone_number: index + 1
        }))
      },
      notification_channel_ids: values.notification_channel_ids && values.notification_channel_ids.length > 0 ? values.notification_channel_ids : undefined,
      fan_overrides: values.fan_overrides
        .filter((override) => override.fan_identifier.trim().length > 0 && override.min_rpm !== null && override.min_rpm !== undefined)
        .map((override) => ({
          fan_identifier: override.fan_identifier.trim(),
          min_rpm: override.min_rpm ?? undefined,  // RPM override - used below first zone threshold
          max_rpm: undefined,  // Not used in simplified model
          lower_temp_c: undefined,  // Not used - follows normal zones
          upper_temp_c: undefined,  // Not used - follows normal zones
          profile: undefined  // Not used
        }))
    };

    // When editing, only include username/password if they have values (user wants to update them)
    // When creating, always include them (they're required)
    if (isEditing) {
      if (values.username.trim()) {
        payload.username = values.username.trim();
      }
      if (values.password.trim()) {
        payload.password = values.password.trim();
      }
    } else {
      payload.username = values.username.trim();
      payload.password = values.password.trim();
    }

    // Include alert configuration
    if (values.alert_config) {
      // Only include enabled alerts in the config
      const enabledAlerts: Record<string, boolean> = {};
      Object.entries(values.alert_config).forEach(([key, enabled]) => {
        if (enabled) {
          enabledAlerts[key] = true;
        }
      });
      payload.alert_config = Object.keys(enabledAlerts).length > 0 ? enabledAlerts : undefined;
    }

    // Include offline alert threshold
    payload.offline_alert_threshold_minutes = values.offline_alert_threshold_minutes || 15;

    try {
      let result;
      if (isEditing && server) {
        result = await updateServer(server.id, payload);
      } else {
        result = await createServer(payload);
      }
      onCreated(result);
      if (!isEditing) {
        form.reset();
        // Reset to default zones after successful submission
        form.setFieldValue('fan_zones', [
          { tempThreshold: 50, targetRpm: 1800 },
          { tempThreshold: 52, targetRpm: 3500 },
          { tempThreshold: 70, targetRpm: 5000 }
        ]);
      }
    } catch (err: any) {
      let detail = 'Unknown error';
      if (err?.response?.data) {
        if (typeof err.response.data === 'string') {
          detail = err.response.data;
        } else if (err.response.data.detail) {
          detail = typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail);
        } else {
          detail = JSON.stringify(err.response.data);
        }
      } else if (err?.message) {
        detail = err.message;
      }
      setError(`Failed to create server: ${detail}. Note: Server config is saved and will be tested during first poll.`);
    } finally {
      setLoading(false);
    }
  });

  return (
    <Paper shadow="sm" radius="md" p="xl" withBorder>
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <div>
            <Title order={3}>{isEditing ? 'Edit Server' : 'Add a Server'}</Title>
            <Text c="dimmed" size="sm">
              {isEditing ? 'Update IPMI connection details and fan behavior.' : 'Configure IPMI connection details and default fan behavior.'}
            </Text>
          </div>
          <TextInput label="Server name" placeholder="Supermicro X11" required {...form.getInputProps('name')} />
          <Select
            label="Vendor"
            data={vendorOptions}
            required
            {...form.getInputProps('vendor', {
              onChange: (value) => {
                form.setFieldValue('vendor', value || 'supermicro');
                form.setFieldValue('bmc_port', getDefaultPort(value || 'supermicro'));
              }
            })}
          />
          <Group grow>
            <TextInput label="BMC host/IP" placeholder="192.168.1.50" required {...form.getInputProps('bmc_host')} />
            <NumberInput 
              label="BMC port" 
              description={`Default: ${getDefaultPort(form.values.vendor)} (standard IPMI)`}
              min={1} 
              max={65535} 
              {...form.getInputProps('bmc_port', { type: 'number' })} 
            />
          </Group>
          <Group grow>
            <NumberInput
              label="Polling interval (seconds)"
              min={30}
              max={86400}
              {...form.getInputProps('poll_interval_seconds', { type: 'number' })}
            />
            <TextInput label="Room / notes" placeholder="Rack in garage" {...form.getInputProps('room_description')} />
          </Group>
          <Group grow>
            <TextInput 
              label="BMC username" 
              required={!isEditing}
              placeholder={isEditing ? 'Leave blank to keep current' : ''}
              {...form.getInputProps('username')} 
            />
            <PasswordInput 
              label="BMC password" 
              required={!isEditing}
              placeholder={isEditing ? 'Leave blank to keep current' : ''}
              {...form.getInputProps('password')} 
            />
          </Group>

          <MultiSelect
            label="Notification channels"
            description="Select which notification channels to use for alerts from this server"
            data={channels}
            placeholder={channelsLoading ? 'Loading channels...' : 'Select notification channels (optional)'}
            searchable
            clearable
            disabled={channelsLoading}
            value={form.values.notification_channel_ids.map(String)}
            onChange={(value) => form.setFieldValue('notification_channel_ids', value.map(Number))}
          />

          <Paper p="md" withBorder radius="md">
            <Stack gap="md">
              <div>
                <Title order={4}>Alert Configuration</Title>
                <Text c="dimmed" size="sm">
                  Enable alerts for hardware issues. Notifications will be sent to selected channels above.
                </Text>
              </div>
              <Group grow>
                <Switch
                  label="Connectivity Issues"
                  description="Alert when server is unreachable or IPMI communication fails"
                  {...form.getInputProps('alert_config.connectivity', { type: 'checkbox' })}
                />
                <Switch
                  label="Memory Errors"
                  description="Alert on memory module errors or failures"
                  {...form.getInputProps('alert_config.memory_errors', { type: 'checkbox' })}
                />
                <Switch
                  label="Power Supply Failure"
                  description="Alert on power supply issues or failures"
                  {...form.getInputProps('alert_config.power_failure', { type: 'checkbox' })}
                />
              </Group>
              <Group grow>
                <Switch
                  label="Chassis Intrusion"
                  description="Alert when chassis is opened or tampered with"
                  {...form.getInputProps('alert_config.intrusion', { type: 'checkbox' })}
                />
                <Switch
                  label="Voltage Issues"
                  description="Alert on voltage abnormalities or failures"
                  {...form.getInputProps('alert_config.voltage_issues', { type: 'checkbox' })}
                />
                <Switch
                  label="System Events"
                  description="Alert on critical system event log entries"
                  {...form.getInputProps('alert_config.system_events', { type: 'checkbox' })}
                />
              </Group>
              <Group grow>
                <Switch
                  label="Critical Temperature"
                  description="Alert when CPU temperature exceeds 80°C"
                  {...form.getInputProps('alert_config.temperature_critical', { type: 'checkbox' })}
                />
              </Group>
              <Group grow>
                <NumberInput
                  label="Offline Alert Threshold (minutes)"
                  description="Alert if server hasn't responded for this many minutes (default: 15)"
                  min={1}
                  max={1440}
                  {...form.getInputProps('offline_alert_threshold_minutes', { type: 'number' })}
                />
              </Group>
            </Stack>
          </Paper>

          <Group justify="space-between" align="center">
            <div>
              <Title order={4}>Fan Curve Configuration</Title>
              <Text c="dimmed" size="sm">
                Configure temperature zones. Fans will ramp up as CPU temperature rises. Default: 3 zones (max 5).
              </Text>
            </div>
            {form.values.fan_zones.length < 5 && (
              <Button
                leftSection={<IconPlus size={16} />}
                variant="light"
                size="xs"
                onClick={addZone}
                type="button"
              >
                Add zone
              </Button>
            )}
          </Group>

          <Stack gap="md">
            {form.values.fan_zones.map((zone, index) => (
              <Paper
                key={index}
                p="md"
                withBorder
                radius="md"
                style={{ backgroundColor: getZoneColor(index) }}
              >
                <Stack gap="xs">
                  <Group justify="space-between">
                    <div>
                      <Text fw={600} size="sm">
                        {getZoneLabel(index, form.values.fan_zones.length)}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {getZoneDescription(index, form.values.fan_zones.length)}
                      </Text>
                    </div>
                    {form.values.fan_zones.length > 1 && (
                      <Button
                        variant="subtle"
                        color="red"
                        size="xs"
                        leftSection={<IconTrash size={14} />}
                        onClick={() => removeZone(index)}
                        type="button"
                      >
                        Remove
                      </Button>
                    )}
                  </Group>
                  <Group grow>
                    <NumberInput
                      label="Temperature threshold (°C)"
                      description={
                        index === 0
                          ? 'Fans switch to this mode below this temp'
                          : `Fans ramp up at ${form.values.fan_zones[index - 1]?.tempThreshold || 'previous'}°C`
                      }
                      placeholder={index === 0 ? '50' : '52'}
                      min={0}
                      max={110}
                      {...form.getInputProps(`fan_zones.${index}.tempThreshold`, { type: 'number' })}
                    />
                    <NumberInput
                      label="Target RPM"
                      description={
                        index === form.values.fan_zones.length - 1
                          ? 'Set to 0 for full speed, or specify RPM'
                          : 'Target RPM for this zone'
                      }
                      placeholder={index === 0 ? '1800' : index === 1 ? '3500' : '5000'}
                      min={0}
                      {...form.getInputProps(`fan_zones.${index}.targetRpm`, { type: 'number' })}
                    />
                  </Group>
                  {index === form.values.fan_zones.length - 1 && (
                    <Text size="xs" c="dimmed" mt="xs">
                      Note: Set Target RPM to 0 to use full fan speed above the previous threshold.
                    </Text>
                  )}
                </Stack>
              </Paper>
            ))}
          </Stack>

          <Paper p="md" withBorder radius="md">
            <Stack gap="md">
              <Group justify="space-between" align="center">
                <div>
                  <Title order={4}>Per-Fan Overrides</Title>
                  <Text c="dimmed" size="sm">
                    Set a custom RPM for specific fans. These fans will run at the override RPM until CPU temp hits the first zone threshold, then follow normal fan zones.
                  </Text>
                </div>
                <Button leftSection={<IconPlus size={16} />} variant="light" onClick={addFanOverride} type="button">
                  Add fan
                </Button>
              </Group>

              <Stack gap="sm">
                {form.values.fan_overrides.map((override, index) => (
                  <Paper key={index} p="md" withBorder radius="md" style={{ backgroundColor: 'var(--mantine-color-dark-6)' }}>
                    <Stack gap="xs">
                      <Group justify="space-between">
                        <Text fw={500}>Fan Override #{index + 1}</Text>
                        <Button
                          variant="subtle"
                          color="red"
                          leftSection={<IconTrash size={16} />}
                          onClick={() => removeFanOverride(index)}
                          type="button"
                        >
                          Remove
                        </Button>
                      </Group>
                      <Group grow>
                        <TextInput
                          label="Fan Identifier"
                          placeholder="FAN1, FAN2, etc."
                          description="The identifier for this fan (e.g., FAN1)"
                          required
                          {...form.getInputProps(`fan_overrides.${index}.fan_identifier`)}
                        />
                        <NumberInput
                          label="RPM Override"
                          placeholder="2200"
                          description="Custom RPM when CPU temp is below first zone threshold (e.g., 52°C). Above that, fan follows normal zones."
                          min={0}
                          required
                          {...form.getInputProps(`fan_overrides.${index}.min_rpm`, { type: 'number' })}
                        />
                      </Group>
                      <Text size="xs" c="dimmed" mt="xs">
                        Example: Set to 2200 RPM. This fan will run at 2200 RPM until CPU reaches 52°C, then it will follow the normal fan zones (3500 RPM at 52°C, 5000 RPM at 70°C, etc.)
                      </Text>
                    </Stack>
                  </Paper>
                ))}
                {form.values.fan_overrides.length === 0 && (
                  <Text c="dimmed" size="sm" ta="center" py="md">
                    No fan overrides configured. Add one to customize individual fan behavior.
                  </Text>
                )}
              </Stack>
            </Stack>
          </Paper>

          {error && (
            <Text c="red" size="sm">
              {error}
            </Text>
          )}

          <Group justify="flex-end">
            {onCancel && (
              <Button variant="subtle" onClick={onCancel} disabled={loading}>
                Cancel
              </Button>
            )}
            <Button type="submit" loading={loading}>
              {isEditing ? 'Update server' : 'Save server'}
            </Button>
          </Group>
        </Stack>
      </form>
    </Paper>
  );
}
