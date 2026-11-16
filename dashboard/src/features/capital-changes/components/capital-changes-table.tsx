import type { UseQueryResult } from '@tanstack/react-query';
import { useSearchParams } from 'react-router';

import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { Pagination } from '@/components/ui/pagination';
import type { ListInterval } from '@/components/ui/period-selector/use-period';
import { formatAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';
import { searchWithPage } from '@/utils/page-number';

import type { CapitalChange, CapitalChangePage } from '../api/get-capital-changes';

const NONE = '—';

type CapitalChangesTableProps = {
  readonly reading: UseQueryResult<CapitalChangePage>;
  readonly interval: ListInterval;
  /** The address of the page of the history, which the pages keep with their filters. */
  readonly path: string;
  /** The history of an account names the flow of each change; that of a flow does not repeat it. */
  readonly withFlow?: boolean;
};

const capitalOf = (amount: string | null, currency: string): string =>
  amount === null ? NONE : `${formatAmount(amount)} ${currency}`;

const columnsOf = (currency: string, withFlow: boolean): DataTableColumn<CapitalChange>[] => [
  { header: 'Data e ora', cell: (change) => formatInstant(change.changed_at) },
  ...(withFlow ? [{ header: 'Flusso', cell: (change: CapitalChange) => change.flow ?? NONE }] : []),
  { header: 'Motivo', cell: (change) => change.reason },
  { header: 'Importo', cell: (change) => capitalOf(change.amount, currency) },
  { header: 'Capitale prima', cell: (change) => capitalOf(change.previous, currency) },
  { header: 'Capitale dopo', cell: (change) => capitalOf(change.new, currency) },
];

const emptyText = (interval: ListInterval): string =>
  interval.from === undefined
    ? 'Nessuna variazione di capitale.'
    : 'Nessuna variazione nel periodo scelto.';

/**
 * The history of the capital in the shared table, with the pages of the API: date and time, reason, amount, capital
 * before and after of each change, from the most recent (R3.4.2, ADR storico-delle-variazioni-di-capitale).
 */
export const CapitalChangesTable = ({
  reading,
  interval,
  path,
  withFlow = false,
}: CapitalChangesTableProps) => {
  const [search] = useSearchParams();
  if (reading.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (reading.data === undefined) {
    return <ErrorMessage error={reading.error} />;
  }
  return (
    <>
      <DataTable
        label="Variazioni di capitale"
        columns={columnsOf(reading.data.currency, withFlow)}
        rows={reading.data.changes}
        rowKey={(change) => `${change.changed_at}-${change.flow_id ?? change.reason}`}
        empty={emptyText(interval)}
      />
      <Pagination
        page={reading.data.page}
        hasNext={reading.data.has_next}
        hrefOf={(target) => `${path}${searchWithPage(search, target)}`}
      />
    </>
  );
};
