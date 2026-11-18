import { useParams } from 'react-router';

import { AccountSettings } from '@/features/accounts/components/account-settings';

/** The tab Impostazioni of the page of the account (R2.3.1, ADR elenco-dei-conti-e-pagina-del-conto). */
export const AccountSettingsRoute = () => {
  const { accountId = '' } = useParams();
  return <AccountSettings accountId={accountId} />;
};
