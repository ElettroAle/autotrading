import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { isComplete, usePeriod } from '@/components/ui/period-selector/use-period';

import { useClosedPositionHistory } from '../api/get-closed-position-history';
import { useCycleHistory } from '../api/get-cycle-history';
import { useAccountOptions, useFlowOptions } from '../api/get-history-options';
import { useOrderHistory } from '../api/get-order-history';
import { useHistorySearch } from '../hooks/use-history-search';
import { apiSearchOf, type HistoryKind } from '../utils/history-search';

import { ClosedPositionHistoryTable } from './closed-position-history-table';
import { CycleHistoryTable } from './cycle-history-table';
import { HistoryFilters } from './history-filters';
import { HistoryResults } from './history-results';
import { HistoryTabs } from './history-tabs';
import { OrderHistoryTable } from './order-history-table';

type ResultsProps = { readonly kind: HistoryKind; readonly query: string; readonly ready: boolean };

// Only the history of the open tab asks the API: the others wait until the user opens them.
const Results = ({ kind, query, ready }: ResultsProps) => {
  const cycles = useCycleHistory(query, ready && kind === 'cycles');
  const positions = useClosedPositionHistory(query, ready && kind === 'closed-positions');
  const orders = useOrderHistory(query, ready && kind === 'orders');
  if (kind === 'cycles') {
    return (
      <HistoryResults pages={cycles} waiting={!ready}>
        {(pages) => <CycleHistoryTable cycles={pages.flatMap((page) => page.cycles)} />}
      </HistoryResults>
    );
  }
  if (kind === 'closed-positions') {
    return (
      <HistoryResults pages={positions} waiting={!ready}>
        {(pages) => (
          <ClosedPositionHistoryTable positions={pages.flatMap((page) => page.positions)} />
        )}
      </HistoryResults>
    );
  }
  return (
    <HistoryResults pages={orders} waiting={!ready}>
      {(pages) => <OrderHistoryTable orders={pages.flatMap((page) => page.orders)} />}
    </HistoryResults>
  );
};

/**
 * The histories of the flows of the user, filtered by flow, version, account, asset and period (R2.5.1): the results
 * are the API's, the page filters nothing itself (ADR 0139).
 */
export const HistoryView = () => {
  const [search, change] = useHistorySearch();
  const [period] = usePeriod();
  const flows = useFlowOptions();
  const accounts = useAccountOptions();
  if (flows.isError) {
    return <ErrorMessage error={flows.error} />;
  }
  if (accounts.isError) {
    return <ErrorMessage error={accounts.error} />;
  }
  if (flows.isPending || accounts.isPending) {
    return <Loading />;
  }
  return (
    <>
      <HistoryTabs current={search.kind} choose={(kind) => change({ kind })} />
      <HistoryFilters search={search} change={change} flows={flows.data} accounts={accounts.data} />
      <Results kind={search.kind} query={apiSearchOf(search, period)} ready={isComplete(period)} />
    </>
  );
};
