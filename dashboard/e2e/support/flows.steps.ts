import { fakePlatform } from '@/testing/mocks/platform';

import { Given, When } from './fixtures';

// Shared by the requirements whose scenarios give a user a flow and nothing more (R2.1.1, R2.4.2).
Given('che {string} ha il flusso {string}', async ({}, account: string, flow: string) => {
  fakePlatform.addUser(account, { hasUserRole: true });
  fakePlatform.addFlow(account, flow);
});

// Shared by the requirements that open the page of the flows (R2.2.2, R2.1.3): a user no background describes is a
// user with the Utente role.
When('{string} apre la pagina dei flussi', async ({ dashboard }, account: string) => {
  fakePlatform.ensureUser(account);
  await dashboard.openAndSignInAs(account);
});
