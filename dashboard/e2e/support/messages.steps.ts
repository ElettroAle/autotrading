import { expect } from '@playwright/test';

import { Then } from './fixtures';

// Shared by the requirements of the dashboard: what the page tells the user, as an alert or as a status.
Then('la dashboard mostra {string}', async ({ dashboard }, message: string) => {
  await expect(dashboard.message(message)).toBeVisible();
});
