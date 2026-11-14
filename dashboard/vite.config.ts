/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

import { runtimeConfigFrom } from './server/runtime-config.ts';

const BASE_PATH = '/dashboard/';

// The development server answers config.json as the container does, from the variables of the shell (ADR 0117).
const runtimeConfigInDevelopment = (): Plugin => ({
  name: 'runtime-config-in-development',
  configureServer(server) {
    server.middlewares.use(`${BASE_PATH}config.json`, (_request, response) => {
      response.setHeader('Content-Type', 'application/json');
      response.end(JSON.stringify(runtimeConfigFrom(process.env)));
    });
  },
});

export default defineConfig({
  base: BASE_PATH,
  plugins: [react(), tailwindcss(), runtimeConfigInDevelopment()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: { port: 5173, strictPort: true },
  test: {
    coverage: {
      provider: 'v8',
      include: ['src/**', 'server/**'],
      exclude: [
        'src/testing/**',
        'src/main.tsx',
        'server/main.ts',
        '**/*.test.{ts,tsx}',
        '**/*.d.ts',
      ],
      reporter: ['text', 'json-summary', 'lcov'],
      reportsDirectory: 'coverage',
      thresholds: { lines: 90, branches: 90, functions: 90, statements: 90 },
    },
    projects: [
      {
        extends: true,
        test: {
          name: 'browser',
          environment: 'jsdom',
          globals: true,
          include: ['src/**/*.test.{ts,tsx}'],
          setupFiles: ['./src/testing/setup-tests.ts'],
          // Instants show in the time zone of the browser: the tests read them in Italy, as the scenarios do.
          env: { TZ: 'Europe/Rome' },
        },
      },
      {
        extends: true,
        test: {
          name: 'node',
          environment: 'node',
          include: ['server/**/*.test.ts', 'architecture/**/*.test.ts'],
        },
      },
    ],
  },
});
