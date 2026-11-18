import { ViewTabs } from '@/components/ui/view-tabs';
import { paths } from '@/config/paths';

/**
 * The tabs of the page of the account, each with an address of its own: the overview, the reconciliation, the history
 * of the capital and the settings (ADR elenco-dei-conti-e-pagina-del-conto).
 */
export const AccountTabs = ({ accountId }: { readonly accountId: string }) => (
  <ViewTabs
    label="Schede del conto"
    views={[
      { name: 'Panoramica', to: paths.account.getHref(accountId) },
      { name: 'Riconciliazione', to: paths.accountReconciliation.getHref(accountId) },
      { name: 'Capitale', to: paths.accountCapital.getHref(accountId) },
      { name: 'Impostazioni', to: paths.accountSettings.getHref(accountId) },
    ]}
  />
);
