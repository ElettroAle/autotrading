import { expect } from '@playwright/test';

import { fakePlatform } from '@/testing/mocks/platform';

import { When } from './fixtures';

// Shared by the access (R2.1.1), where the session has expired and the sign-in waits for the user, and by the results
// of the flows (R6.4.2), where the user signs in and reads the page.
When(
  '{string} apre la pagina del flusso {string}',
  async ({ dashboard, memory }, account: string, flow: string) => {
    memory.account = account;
    memory.flow = flow;
    await dashboard.openFlow(flow);
    if (fakePlatform.sessionsExpired()) {
      return;
    }
    await dashboard.signInAs(account);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);

// Shared by the suspension of the openings for maximum loss (R3.2.2) and for an alarm of reconciliation (R3.3.2): the
// page of the flow shows both with the same notice.
When(
  '{string} apre il flusso {string} nella dashboard',
  async ({ dashboard }, account: string, flow: string) => {
    await dashboard.openFlowAs(account, flow);
    await expect(dashboard.flowName()).toHaveText(flow);
  },
);
