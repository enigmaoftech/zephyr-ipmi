#!/usr/bin/env node
/**
 * Simple HTTP server that redirects all requests to HTTPS frontend.
 * Runs on port 5174 by default, redirects to HTTPS on port 5173.
 */

import http from 'http';

const httpsPort = 5173;
const httpPort = process.argv[2] ? parseInt(process.argv[2]) : 5174;

const server = http.createServer((req, res) => {
  const host = req.headers.host?.split(':')[0] || 'localhost';
  const httpsUrl = `https://${host}:${httpsPort}${req.url}`;
  
  res.writeHead(301, {
    'Location': httpsUrl,
    'Content-Type': 'text/plain'
  });
  res.end(`Redirecting to ${httpsUrl}`);
});

server.listen(httpPort, '0.0.0.0', () => {
  console.log(`🔄 HTTP redirect server running on port ${httpPort}`);
  console.log(`   Redirecting all HTTP requests to HTTPS on port ${httpsPort}`);
});

// Handle errors gracefully
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`❌ Port ${httpPort} is already in use`);
    process.exit(1);
  } else {
    console.error('❌ Server error:', err);
    process.exit(1);
  }
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Stopping HTTP redirect server...');
  server.close(() => {
    process.exit(0);
  });
});

process.on('SIGTERM', () => {
  server.close(() => {
    process.exit(0);
  });
});

