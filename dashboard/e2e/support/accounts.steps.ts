import { When } from './fixtures';

// Shared by the summary of the accounts (R2.2.1) and the state of their reconciliation (R3.3.2).
When('{string} apre la pagina dei conti', async ({ dashboard }, account: string) => {
  await dashboard.openAccounts();
  await dashboard.signInAs(account);
});
