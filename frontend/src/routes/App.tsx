import { AppShell, Button, Center, Group, Loader, NavLink, Stack, Text } from '@mantine/core';
import { IconBell, IconPlus, IconSettings, IconServer } from '@tabler/icons-react';
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';

import LoginForm from '../components/LoginForm';
import NotificationSettings from '../components/NotificationSettings';
import ServerForm from '../components/ServerForm';
import ServerList from '../components/ServerList';
import UserProfile from '../components/UserProfile';
import { deleteServer, fetchServers, getCurrentUser, logout } from '../services/api';
import type { Server, User } from '../types/api';

export default function App() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [initialised, setInitialised] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('servers');
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [editingServer, setEditingServer] = useState<Server | null>(null);
  const [showForm, setShowForm] = useState<boolean>(false);

  const loadServers = useCallback(async () => {
    setLoading(true);
    setStatusMessage(null);
    try {
      const data = await fetchServers();
      setServers(data);
      setIsAuthenticated(true);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 401) {
        setIsAuthenticated(false);
      } else {
        setStatusMessage('Unable to load servers right now.');
      }
    } finally {
      setLoading(false);
      setInitialised(true);
    }
  }, []);

  const loadUser = useCallback(async () => {
    try {
      const user = await getCurrentUser();
      setCurrentUser(user);
    } catch (err) {
      console.error('Failed to load user:', err);
    }
  }, []);

  const handleUserUpdate = useCallback(async () => {
    await loadUser();
  }, [loadUser]);

  useEffect(() => {
    void loadServers();
    if (isAuthenticated) {
      void loadUser();
    }
  }, [loadServers, isAuthenticated, loadUser]);

  const handleLoginSuccess = async () => {
    setIsAuthenticated(true);
    await Promise.all([loadServers(), loadUser()]);
  };

  const handleServerCreated = (server: Server) => {
    if (editingServer) {
      // Update existing server in list
      setServers((prev) => prev.map((s) => (s.id === server.id ? server : s)));
      setStatusMessage('Server updated successfully.');
      setEditingServer(null);
      setShowForm(false);
    } else {
      // Add new server to list
      setServers((prev) => [server, ...prev]);
      setStatusMessage('Server saved and scheduled for monitoring.');
      setShowForm(false);
    }
  };

  const handleServerEdit = (server: Server) => {
    setEditingServer(server);
    setShowForm(true);
    // Scroll to form (form will populate with server data)
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleAddServer = () => {
    setEditingServer(null);
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCancelForm = () => {
    setEditingServer(null);
    setShowForm(false);
  };

  const handleServerDelete = async (serverId: number) => {
    if (window.confirm('Are you sure you want to delete this server? This will stop monitoring.')) {
      try {
        await deleteServer(serverId);
        setServers((prev) => prev.filter((s) => s.id !== serverId));
        setStatusMessage('Server deleted successfully.');
        if (editingServer?.id === serverId) {
          setEditingServer(null);
        }
      } catch (err: any) {
        const detail = err?.response?.data?.detail || err?.message || 'Failed to delete server';
        setStatusMessage(`Failed to delete server: ${detail}`);
      }
    }
  };

  const handleLogout = async () => {
    await logout();
    setIsAuthenticated(false);
    setServers([]);
  };

  if (!initialised && loading) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  if (!isAuthenticated) {
    return <LoginForm onSuccess={handleLoginSuccess} />;
  }

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{ width: 200, breakpoint: 'sm' }}
      padding="md"
      styles={{ main: { backgroundColor: 'var(--mantine-color-dark-7)' } }}
    >
      <AppShell.Header>
        <Stack
          align="center"
          justify="center"
          style={{ height: '100%' }}
          gap={0}
        >
          <Text fw={600}>Zephyr IPMI</Text>
          {currentUser && (
            <Text size="xs" c="dimmed">
              {currentUser.username}
            </Text>
          )}
        </Stack>
      </AppShell.Header>
      <AppShell.Navbar p="md">
        <Stack gap="xs">
          <NavLink
            label="Servers"
            leftSection={<IconServer size={16} />}
            active={activeTab === 'servers'}
            onClick={() => {
              setActiveTab('servers');
              setShowForm(false);
              setEditingServer(null);
            }}
          />
          <NavLink
            label="Notifications"
            leftSection={<IconBell size={16} />}
            active={activeTab === 'notifications'}
            onClick={() => {
              setActiveTab('notifications');
              setShowForm(false);
              setEditingServer(null);
            }}
          />
          <NavLink
            label="Profile"
            leftSection={<IconSettings size={16} />}
            active={activeTab === 'profile'}
            onClick={() => {
              setActiveTab('profile');
              setShowForm(false);
              setEditingServer(null);
            }}
          />
          <Button variant="subtle" color="gray" size="sm" mt="auto" onClick={handleLogout}>
            Sign out
          </Button>
        </Stack>
      </AppShell.Navbar>
      <AppShell.Main>
        <Stack gap="xl">
          {statusMessage && (
            <Text c="green" size="sm">
              {statusMessage}
            </Text>
          )}
          {activeTab === 'servers' && (
            <>
              <Group justify="space-between" align="center">
                <Text size="xl" fw={600}>Servers</Text>
                {!showForm && (
                  <Button
                    leftSection={<IconPlus size={16} />}
                    onClick={handleAddServer}
                  >
                    Add Server
                  </Button>
                )}
              </Group>
              {showForm && (
                <ServerForm
                  server={editingServer}
                  onCreated={handleServerCreated}
                  onCancel={handleCancelForm}
                />
              )}
              {loading ? (
                <Center>
                  <Loader />
                </Center>
              ) : (
                <ServerList servers={servers} onEdit={handleServerEdit} onDelete={handleServerDelete} />
              )}
            </>
          )}
          {activeTab === 'notifications' && <NotificationSettings onUpdate={handleUserUpdate} />}
          {activeTab === 'profile' && currentUser && (
            <UserProfile user={currentUser} onUpdate={handleUserUpdate} />
          )}
        </Stack>
      </AppShell.Main>
    </AppShell>
  );
}
