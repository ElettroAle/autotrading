import { expect } from '@playwright/test';

import { fakePlatform, flowIdOf } from '@/testing/mocks/platform';

import { Then } from './fixtures';

// The confirmation a command that closes positions asks before it runs: the cash-out (R3.4.1) and the emergency
// closing (R3.2.3) share the window and these steps.
Then('la dashboard chiede conferma con {string}', async ({ dashboard }, question: string) => {
  await expect(dashboard.page.getByRole('alertdialog')).toContainText(question);
});

Then(
  'nessuna posizione viene chiusa finché {string} non conferma',
  async ({ dashboard, memory }, account: string) => {
    expect(memory.account).toBe(account);
    await expect(dashboard.page.getByRole('alertdialog')).toBeVisible();
    expect(fakePlatform.cashOutsOf(memory.flow)).toBe(0);
    expect(fakePlatform.emergencyClosings()).toBe(0);
    expect(fakePlatform.openPositionsOf(flowIdOf(memory.flow))).not.toHaveLength(0);
  },
);
