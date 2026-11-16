import { useAccounts } from '../api/get-accounts';

/**
 * The title of a page of an account, once the page has read it: what the page shows with the name of the account,
 * «Allarmi del conto test-1». Before, the title says only the subject.
 */
export const useAccountTitle = (accountId: string, subject: string): string => {
  const name = useAccounts().data?.find((account) => account.id === accountId)?.name;
  return name === undefined ? subject : `${subject} del conto ${name}`;
};
