import { expect } from '@playwright/test';

import { Then } from './fixtures';

// Shared by the requirements of the dashboard: what the page tells the user, as an alert or as a status.
Then('la dashboard mostra {string}', async ({ dashboard }, message: string) => {
  await expect(dashboard.message(message)).toBeVisible();
});

// Shared by the commands of the flows (R2.3.4) and the accounts (R2.3.1): the step that caused it names the reason.
Then('la dashboard mostra il motivo del rifiuto', async ({ dashboard, memory }) => {
  await expect(dashboard.alert()).toContainText(memory.refusal);
});
