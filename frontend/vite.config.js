import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// The browser talks to one origin; the dev server forwards API and WebSocket traffic.
const target = process.env.CONNECT_API_URL ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': target, '/ws': { target, ws: true } } },
});
