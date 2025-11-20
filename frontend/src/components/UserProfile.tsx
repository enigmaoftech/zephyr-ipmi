import { Button, Group, Paper, PasswordInput, Stack, Text, TextInput, Title } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useState } from 'react';

import { changePassword, changeUsername, getCurrentUser } from '../services/api';
import type { User } from '../types/api';

interface UserProfileProps {
  user: User;
  onUpdate: () => void;
}

export default function UserProfile({ user, onUpdate }: UserProfileProps) {
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [usernameLoading, setUsernameLoading] = useState(false);

  const passwordForm = useForm({
    initialValues: {
      current_password: '',
      new_password: '',
      confirm_password: ''
    },
    validate: {
      current_password: (value) => (value.trim().length >= 8 ? null : 'Current password required'),
      new_password: (value) => (value.trim().length >= 8 ? null : 'New password must be at least 8 characters'),
      confirm_password: (value, values) =>
        value === values.new_password ? null : 'Passwords do not match'
    }
  });

  const usernameForm = useForm({
    initialValues: {
      new_username: user.username
    },
    validate: {
      new_username: (value) => (value.trim().length >= 3 ? null : 'Username must be at least 3 characters')
    }
  });

  const handlePasswordChange = passwordForm.onSubmit(async (values) => {
    setPasswordError(null);
    setPasswordLoading(true);
    try {
      await changePassword({
        current_password: values.current_password,
        new_password: values.new_password
      });
      passwordForm.reset();
      onUpdate();
      setPasswordError('Password updated successfully!');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to update password';
      setPasswordError(detail);
    } finally {
      setPasswordLoading(false);
    }
  });

  const handleUsernameChange = usernameForm.onSubmit(async (values) => {
    if (values.new_username.toLowerCase() === user.username.toLowerCase()) {
      setUsernameError('New username must be different from current username');
      return;
    }
    setUsernameError(null);
    setUsernameLoading(true);
    try {
      await changeUsername({ new_username: values.new_username });
      onUpdate();
      setUsernameError('Username updated successfully!');
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Failed to update username';
      setUsernameError(detail);
    } finally {
      setUsernameLoading(false);
    }
  });

  return (
    <Stack gap="xl">
      <div>
        <Title order={3}>User Profile</Title>
        <Text c="dimmed" size="sm">
          Manage your account settings
        </Text>
      </div>

      <Paper shadow="sm" radius="md" p="xl" withBorder>
        <form onSubmit={handlePasswordChange}>
          <Stack gap="md">
            <Title order={4}>Change Password</Title>
            <PasswordInput
              label="Current password"
              required
              {...passwordForm.getInputProps('current_password')}
            />
            <PasswordInput
              label="New password"
              required
              {...passwordForm.getInputProps('new_password')}
            />
            <PasswordInput
              label="Confirm new password"
              required
              {...passwordForm.getInputProps('confirm_password')}
            />
            {passwordError && (
              <Text c={passwordError.includes('success') ? 'green' : 'red'} size="sm">
                {passwordError}
              </Text>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={passwordLoading}>
                Update password
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>

      <Paper shadow="sm" radius="md" p="xl" withBorder>
        <form onSubmit={handleUsernameChange}>
          <Stack gap="md">
            <Title order={4}>Change Username</Title>
            <TextInput
              label="Current username"
              value={user.username}
              disabled
            />
            <TextInput
              label="New username"
              required
              {...usernameForm.getInputProps('new_username')}
            />
            {usernameError && (
              <Text c={usernameError.includes('success') ? 'green' : 'red'} size="sm">
                {usernameError}
              </Text>
            )}
            <Group justify="flex-end">
              <Button type="submit" loading={usernameLoading}>
                Update username
              </Button>
            </Group>
          </Stack>
        </form>
      </Paper>
    </Stack>
  );
}
