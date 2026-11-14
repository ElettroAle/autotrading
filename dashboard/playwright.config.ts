import { defineConfig, devices } from '@playwright/test';
import { cucumberReporter, defineBddConfig } from 'playwright-bdd';

import { FAKE_IDENTITY_PROVIDER } from './src/testing/mocks/identity-provider.ts';

const PORT = 4173;
const ORIGIN = `http://127.0.0.1:${PORT}`;

// The scenarios of the dashboard run on the .feature files of specs/, as pytest-bdd does for Python (ADR 0116).
const testDir = defineBddConfig({
  features: '../specs/E2-dashboard-e-confronto/**/*.feature',
  featuresRoot: '../specs',
  steps: ['e2e/support/fixtures.ts', 'e2e/support/*.steps.ts', 'e2e/scenarios/**/*.steps.ts'],
  tags: 'not @wip and not @pipeline',
});

export default defineConfig({
  testDir,
  tsconfig: './tsconfig.node.json',
  forbidOnly: true,
  fullyParallel: true,
  reporter: [['list'], cucumberReporter('json', { outputFile: 'reports/cucumber.json' })],
  // The dashboard shows instants in the time zone of the browser: the scenarios read times of a day in Italy.
  use: {
    ...devices['Desktop Chrome'],
    baseURL: ORIGIN,
    timezoneId: 'Europe/Rome',
    trace: 'retain-on-failure',
  },
  // The build of the image, served by the server of the image, configured as an installation dev (ADR 0117).
  webServer: {
    command: 'npx vite build && node server/main.ts',
    url: `${ORIGIN}/dashboard/health`,
    reuseExistingServer: false,
    timeout: 180_000,
    env: {
      DASHBOARD_PORT: String(PORT),
      APP_ENVIRONMENT: 'dev',
      AUTH_ISSUER: FAKE_IDENTITY_PROVIDER.issuer,
      AUTH_CLIENT_ID: FAKE_IDENTITY_PROVIDER.clientId,
      AUTH_SCOPE: FAKE_IDENTITY_PROVIDER.scope,
    },
  },
});
