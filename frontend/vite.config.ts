import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');

  // Check if SSL certificates exist for frontend HTTPS
  const certDir = path.resolve(__dirname, 'certs');
  const certFile = path.join(certDir, 'zephyr-frontend.crt');
  const keyFile = path.join(certDir, 'zephyr-frontend.key');
  
  let httpsConfig = undefined;
  if (fs.existsSync(certFile) && fs.existsSync(keyFile)) {
    httpsConfig = {
      key: fs.readFileSync(keyFile),
      cert: fs.readFileSync(certFile),
    };
  }

  return {
    plugins: [react()],
    server: {
      port: 5173,
      https: httpsConfig,
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL ?? 'https://localhost:8443',
          changeOrigin: true,
          secure: false, // Allow self-signed certificates
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    },
    build: {
      outDir: 'dist'
    }
  };
});
