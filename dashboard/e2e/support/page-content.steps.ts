import { expect } from '@playwright/test';

import { Then } from './fixtures';

// Shared by the requirements whose pages say in words that there is nothing to show (R2.2.3, R2.2.4, R2.2.5).
Then('la pagina mostra {string}', async ({ dashboard }, message: string) => {
  await expect(dashboard.content()).toContainText(message);
});
