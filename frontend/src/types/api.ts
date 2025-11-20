export interface User {
  id: number;
  username: string;
  role: string;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ServerFanOverride {
  id?: number;
  fan_identifier: string;
  min_rpm?: number | null;
  max_rpm?: number | null;
  lower_temp_c?: number | null;
  upper_temp_c?: number | null;
  profile?: Record<string, unknown> | null;
  created_at?: string;
}

export interface Server {
  id: number;
  name: string;
  vendor: string;
  bmc_host: string;
  bmc_port: number;
  poll_interval_seconds: number;
  fan_defaults?: Record<string, unknown> | null;
  notification_channel_ids?: number[] | null;
  alert_config?: Record<string, boolean> | null;
  offline_alert_threshold_minutes?: number;
  created_at: string;
  fan_overrides: ServerFanOverride[];
  metadata?: Record<string, unknown> | null;
}

export interface ServerCreateRequest {
  name: string;
  vendor: string;
  bmc_host: string;
  bmc_port: number;
  poll_interval_seconds: number;
  username?: string;
  password?: string;
  metadata?: Record<string, unknown> | null;
  fan_defaults?: Record<string, unknown> | null;
  notification_channel_ids?: number[] | null;
  alert_config?: Record<string, boolean> | null;
  offline_alert_threshold_minutes?: number;
  fan_overrides?: ServerFanOverride[] | null;
}
