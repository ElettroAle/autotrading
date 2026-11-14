import { fakePlatform } from '@/testing/mocks/platform';

import { Given } from './fixtures';

// Shared by the requirements whose scenarios give a user a flow and nothing more (R2.1.1, R2.4.2).
Given('che {string} ha il flusso {string}', async ({}, account: string, flow: string) => {
  fakePlatform.addUser(account, { hasUserRole: true });
  fakePlatform.addFlow(account, flow);
});
