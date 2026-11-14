import { expect } from '@playwright/test';

import { Then } from './fixtures';

// Shared by the requirements whose scenarios end on a message of the dashboard (R2.1.1, R2.3.6).
Then('la dashboard mostra {string}', async ({ dashboard }, message: string) => {
  await expect(dashboard.message(message)).toBeVisible();
});
