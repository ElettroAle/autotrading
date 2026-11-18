import { useAccount } from '../hooks/use-account';

import { ReconciliationStatus } from './reconciliation-status';
import { UnattributableMovements } from './unattributable-movements';

/**
 * The tab Riconciliazione of the page of the account: the last comparison with the threshold and its commands, the
 * link to the alerts of the account, then the movements no flow explains (R3.3.2, R1.6.2, ADR
 * elenco-dei-conti-e-pagina-del-conto). The page has read the account before its tabs show.
 */
export const AccountReconciliation = ({ accountId }: { readonly accountId: string }) => {
  const account = useAccount(accountId);
  if (account === undefined) {
    return null;
  }
  return (
    <div className="min-w-0 space-y-4 rounded border border-slate-200 bg-white p-4">
      <ReconciliationStatus account={account} />
      <UnattributableMovements account={account} />
    </div>
  );
};
