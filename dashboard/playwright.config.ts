import { defineConfig, devices } from '@playwright/test';
import { cucumberReporter, defineBddConfig } from 'playwright-bdd';

import { FAKE_IDENTITY_PROVIDER } from './src/testing/mocks/identity-provider.ts';

const TIME_ZONE = 'Europe/Rome';

// The steps build the instants of a scenario with the clock of Node, the page reads them with the clock of the
// browser: both run in the same zone, whatever the zone of the machine (R2.1.2). The workers inherit it.
process.env.TZ = TIME_ZONE;

const PORT = 4173;
const ORIGIN = `http://127.0.0.1:${PORT}`;

// The scenarios of the dashboard run on the .feature files of specs/, as pytest-bdd does for Python (ADR 0116).
const testDir = defineBddConfig({
  features: '../specs/E2-dashboard-e-confronto/**/*.feature',
  featuresRoot: '../specs',
  steps: ['e2e/support/fixtures.ts', 'e2e/support/**/*.steps.ts', 'e2e/scenarios/**/*.steps.ts'],
  tags: 'not @wip and not @pipeline',
  // A scenario of what the worker does (the equity a cycle records) has no step here: pytest-bdd runs it on the use
  // cases, and the coverage of the scenarios reads both reports (ADR 0116).
  missingSteps: 'skip-scenario',
});

export default defineConfig({
  tsconfig: './tsconfig.node.json',
  forbidOnly: true,
  fullyParallel: true,
  reporter: [['list'], cucumberReporter('json', { outputFile: 'reports/cucumber.json' })],
  // The dashboard shows instants in the time zone of the browser: the scenarios read times of a day in Italy.
  use: {
    baseURL: ORIGIN,
    timezoneId: TIME_ZONE,
    trace: 'retain-on-failure',
  },
  // The scenarios on a desktop; the layout of the forms also on the width of a phone (ADR 0146).
  projects: [
    { name: 'scenari', testDir, use: { ...devices['Desktop Chrome'] } },
    { name: 'telefono', testDir: './e2e/layout', use: { ...devices['Pixel 7'] } },
  ],
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
