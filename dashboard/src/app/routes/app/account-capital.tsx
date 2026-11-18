import { useParams, useSearchParams } from 'react-router';

import { PeriodSelector } from '@/components/ui/period-selector/period-selector';
import { AccountCapitalChanges } from '@/features/capital-changes/components/account-capital-changes';
import { pageOf } from '@/utils/page-number';

/**
 * The tab Capitale of the page of the account: the history of its capital under the period it is filtered by (R3.4.2,
 * ADR elenco-dei-conti-e-pagina-del-conto).
 */
export const AccountCapitalRoute = () => {
  const { accountId = '' } = useParams();
  const [search] = useSearchParams();
  return (
    <div className="space-y-4">
      <PeriodSelector />
      <AccountCapitalChanges accountId={accountId} page={pageOf(search.get('page'))} />
    </div>
  );
};
