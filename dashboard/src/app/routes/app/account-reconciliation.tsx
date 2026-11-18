import { useParams } from 'react-router';

import { AccountReconciliation } from '@/features/accounts/components/account-reconciliation';

/** The tab Riconciliazione of the page of the account (R3.3.2, ADR elenco-dei-conti-e-pagina-del-conto). */
export const AccountReconciliationRoute = () => {
  const { accountId = '' } = useParams();
  return <AccountReconciliation accountId={accountId} />;
};
