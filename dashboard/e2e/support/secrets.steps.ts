import { expect } from '@playwright/test';

import { Then } from './fixtures';

const PAGES = ['/', '/accounts', '/provider-keys'];

// Shared by the requirements whose forms take a secret (R2.3.1, R2.3.2): it is never shown again after the sending.
Then('la chiave non è visibile in alcuna pagina', async ({ dashboard, memory }) => {
  expect(memory.secret).not.toBe('');
  expect(await dashboard.shows(memory.secret)).toBe(false);
  for (const path of PAGES) {
    await dashboard.open(path);
    await expect(dashboard.pageHeading()).toBeVisible();
    expect(await dashboard.shows(memory.secret), `la chiave compare in ${path}`).toBe(false);
  }
});
