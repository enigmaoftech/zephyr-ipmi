import { Anchor, Button, Center, Container, Loader, Paper, PasswordInput, Stack, Text, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useEffect, useState } from 'react';

import axios from 'axios';
import { fetchAuthStatus, login, register } from '../services/api';

interface LoginFormProps {
  onSuccess: () => void;
}

export default function LoginForm({ onSuccess }: LoginFormProps) {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [hasUsers, setHasUsers] = useState<boolean | null>(null);

  useEffect(() => {
    const loadStatus = async () => {
      try {
        const status = await fetchAuthStatus();
        setHasUsers(status.has_users);
        setMode(status.has_users ? 'login' : 'register');
      } catch (err) {
        // If status check fails, default to register so first-time setup is not blocked.
        setHasUsers(false);
        setMode('register');
      }
    };

    void loadStatus();
  }, []);

  const form = useForm({
    initialValues: {
      username: '',
      password: ''
    },
    validate: {
      username: (value) => (value.trim().length >= 3 ? null : 'Username must be at least 3 characters'),
      password: (value) => (value.trim().length >= 8 ? null : 'Password must be at least 8 characters')
    }
  });

  const handleSubmit = form.onSubmit(async (values) => {
    setError(null);
    setLoading(true);
    try {
      if (mode === 'register') {
        console.log('Attempting to register user:', values.username);
        await register(values);
        console.log('Registration successful');
        setHasUsers(true);
        setMode('login');
        // After successful registration, immediately log in with the same credentials.
        try {
          console.log('Attempting to login after registration');
          await login(values);
          console.log('Login successful, calling onSuccess');
          onSuccess();
          return;
        } catch (loginErr) {
          console.error('Login after registration failed:', loginErr);
          if (axios.isAxiosError(loginErr)) {
            const detail = loginErr.response?.data?.detail || 'Unknown error';
            setError(`Account created, but login failed: ${detail}. Please try signing in.`);
          } else {
            setError('Account created, but login failed. Please try signing in.');
          }
          return;
        }
      }
      console.log('Attempting to login:', values.username);
      await login(values);
      console.log('Login successful');
      onSuccess();
    } catch (err) {
      console.error('Auth error:', err);
      if (axios.isAxiosError(err)) {
        console.error('Error details:', err.response?.status, err.response?.data);
        if (err.response?.status === 409 && mode === 'register') {
          const detail = err.response?.data?.detail || '';
          if (detail.includes('already exists')) {
            setError('Admin already exists. Please sign in instead.');
          } else {
            setError('That username is already in use. Try another.');
          }
        } else {
          const detail = err.response?.data?.detail || err.message || 'Unknown error';
          setError(
            mode === 'register'
              ? `Account creation failed: ${detail}`
              : `Login failed: ${detail}`
          );
        }
      } else {
        setError(
          mode === 'register'
            ? `Account creation failed: ${String(err)}`
            : `Login failed: ${String(err)}`
        );
      }
    } finally {
      setLoading(false);
    }
  });

  if (hasUsers === null) {
    return (
      <Center h="100vh">
        <Loader />
      </Center>
    );
  }

  return (
    <Container size={420} my={80}>
      <Text ta="center" size="xl" fw={700}>
        Zephyr IPMI
      </Text>
      <Text ta="center" c="dimmed" size="sm" mt="xs">
        {mode === 'login' ? 'Sign in to configure your servers' : 'Create the first admin user'}
      </Text>
      <Paper withBorder shadow="sm" p="lg" mt="xl" radius="md">
        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput label="Username" placeholder="admin" required {...form.getInputProps('username')} />
            <PasswordInput label="Password" placeholder="••••••••" required {...form.getInputProps('password')} />
            {error && (
              <Text c="red" size="sm">
                {error}
              </Text>
            )}
            <Button type="submit" loading={loading} fullWidth>
              {mode === 'login' ? 'Sign in' : 'Create admin user'}
            </Button>
            {hasUsers && (
              <Text ta="center" c="dimmed" size="xs">
                First time here?{' '}
                <Anchor component="button" type="button" size="xs" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
                  {mode === 'login' ? 'Create admin user' : 'Sign in instead'}
                </Anchor>
              </Text>
            )}
            {!hasUsers && (
              <Text ta="center" c="dimmed" size="xs">
                This appears to be the first launch. Create the initial admin user to get started.
              </Text>
            )}
          </Stack>
        </form>
      </Paper>
    </Container>
  );
}
