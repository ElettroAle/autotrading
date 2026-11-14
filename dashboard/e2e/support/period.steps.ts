import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { When } from './fixtures';

// Shared by the panels that read the period of the page (R2.2.3, R2.2.6, R2.4.2; ADR 0123): the page is the one the
// scenario named, or the flow it prepared, its histories waiting for the user when the scenario gave any.
When(
  '{string} sceglie il periodo {string}',
  async ({ dashboard, memory }, account: string, period: string) => {
    if (!fakePlatform.hasUser(account)) {
      fakePlatform.addUser(account, { hasUserRole: true });
    }
    for (const [name, history] of memory.histories) {
      fakePlatform.addFlow(account, name, { history });
    }
    const [historyFlow] = [...memory.histories.keys()];
    if (memory.periodPage === '') {
      await dashboard.openFlow(historyFlow ?? memory.flow);
    } else {
      await dashboard.open(memory.periodPage);
    }
    await dashboard.signInAs(account);
    await expect(dashboard.period()).toBeVisible();
    await dashboard.period().selectOption({ label: period });
  },
);
