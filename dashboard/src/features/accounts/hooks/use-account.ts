import { useAccounts, type Account } from '../api/get-accounts';

/** The account of the tenant with the id, from the same reading of the accounts as the list; undefined until read. */
export const useAccount = (accountId: string): Account | undefined =>
  useAccounts().data?.find((account) => account.id === accountId);
