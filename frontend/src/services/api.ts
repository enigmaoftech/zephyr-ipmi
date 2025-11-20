import axios from 'axios';

import type { LoginRequest, Server, ServerCreateRequest, User } from '../types/api';

// Use Vite proxy in development, or direct backend URL
// Force use of proxy in dev mode to avoid CORS issues
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';

console.log('API baseURL configured:', baseURL, 'DEV:', import.meta.env.DEV);

const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 10000
});

// Add request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url, config.data);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for debugging
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.message, error.config?.url, error.response?.status, error.response?.data);
    return Promise.reject(error);
  }
);

export async function login(payload: LoginRequest) {
  try {
    const response = await api.post('/auth/login', payload);
    console.log('Login API response:', response.status, response.data);
    return response;
  } catch (error) {
    console.error('Login API error:', error);
    throw error;
  }
}

export async function register(payload: LoginRequest) {
  try {
    const response = await api.post('/auth/register', { ...payload, role: 'admin' });
    console.log('Register API response:', response.status, response.data);
    return response;
  } catch (error) {
    console.error('Register API error:', error);
    throw error;
  }
}

export async function fetchAuthStatus(): Promise<{ has_users: boolean }> {
  const { data } = await api.get<{ has_users: boolean }>('/auth/status');
  return data;
}

export async function logout() {
  await api.post('/auth/logout');
}

export async function fetchServers(): Promise<Server[]> {
  const { data } = await api.get<Server[]>('/servers/');
  return data;
}

export async function createServer(payload: ServerCreateRequest): Promise<Server> {
  const { data } = await api.post<Server>('/servers/', payload);
  return data;
}

export async function updateServer(serverId: number, payload: ServerCreateRequest): Promise<Server> {
  const { data } = await api.put<Server>(`/servers/${serverId}`, payload);
  return data;
}

export async function deleteServer(serverId: number): Promise<void> {
  await api.delete(`/servers/${serverId}`);
}

export async function getServer(serverId: number): Promise<Server> {
  const { data } = await api.get<Server>(`/servers/${serverId}`);
  return data;
}

export async function testServerConnection(serverId: number): Promise<{ status: string; message: string }> {
  const { data } = await api.post<{ status: string; message: string }>(`/servers/${serverId}/test`);
  return data;
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

export async function changePassword(payload: { current_password: string; new_password: string }): Promise<User> {
  const { data } = await api.put<User>('/auth/password', payload);
  return data;
}

export async function changeUsername(payload: { new_username: string }): Promise<User> {
  const { data } = await api.put<User>('/auth/username', payload);
  return data;
}

export async function fetchChannels(): Promise<any[]> {
  const { data } = await api.get<any[]>('/notifications/channels');
  return data;
}

export async function createChannel(payload: any): Promise<any> {
  const { data } = await api.post<any>('/notifications/channels', payload);
  return data;
}

export async function deleteChannel(channelId: number): Promise<void> {
  await api.delete(`/notifications/channels/${channelId}`);
}

export async function testChannel(channelId: number): Promise<{ status: string; message: string }> {
  const { data } = await api.post<{ status: string; message: string }>(`/notifications/channels/${channelId}/test`);
  return data;
}

export interface ActiveAlert {
  id: number;
  server_id: number;
  alert_type: string;
  message: string;
  first_triggered_at: string;
  last_updated_at: string;
  cleared_at: string | null;
  cleared_by: string | null;
}

export async function getServerAlerts(serverId: number): Promise<ActiveAlert[]> {
  const { data } = await api.get<ActiveAlert[]>(`/servers/${serverId}/alerts`);
  return data;
}

export async function getAllAlerts(): Promise<ActiveAlert[]> {
  const { data } = await api.get<ActiveAlert[]>('/servers/alerts/all');
  return data;
}

export async function clearServerAlert(serverId: number, alertType: string): Promise<{ status: string; message: string }> {
  const { data } = await api.post<{ status: string; message: string }>(`/servers/${serverId}/alerts/${alertType}/clear`);
  return data;
}

export default api;
