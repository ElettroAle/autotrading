import { useParams } from 'react-router';

import { AccountOverview } from '@/features/accounts/components/account-overview';

/** The tab Panoramica of the page of the account, the one it opens on (ADR elenco-dei-conti-e-pagina-del-conto). */
export const AccountOverviewRoute = () => {
  const { accountId = '' } = useParams();
  return <AccountOverview accountId={accountId} />;
};
