import { CommandButton } from '@/components/ui/command-button';
import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import {
  listIntervalOf,
  PERIODS,
  type PeriodKind,
} from '@/components/ui/period-selector/use-period';
import { useTableFilters, type TableFilter } from '@/hooks/use-table-filters';
import { formatAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import type { Account } from '../api/get-accounts';
import {
  useUnattributable,
  type Unattributable,
  type UnattributableKind,
  type UnattributablePage,
  type UnattributableQuery,
} from '../api/get-unattributable';

const TITLE = 'Movimenti non spiegati';

const KIND_LABELS: Readonly<Record<UnattributableKind, string>> = {
  'variazione del saldo': 'Variazione del saldo',
  posizione: 'Posizione',
  esecuzione: 'Esecuzione',
};

// The period the record opens on is the last 24 hours: the choice that does not narrow further is that one.
const DEFAULT_PERIOD: PeriodKind = '24h';
const WIDER_PERIODS: readonly PeriodKind[] = ['7d', '30d', 'all'];
// The same words of the shared selector of the period.
const PERIOD_LABELS = Object.fromEntries(
  PERIODS.map(({ kind, label }) => [kind, label]),
) as Readonly<Record<PeriodKind, string>>;

type Totals = Pick<UnattributablePage, 'count' | 'net_change'>;

const NO_TOTALS: Totals = { count: 0, net_change: '0' };

// Every account of the page has its own filters in the address: the names carry the account.
const kindFilterOf = (accountId: string): string => `${accountId}.kind`;
const periodFilterOf = (accountId: string): string => `${accountId}.period`;

const filtersOf = (accountId: string): TableFilter[] => [
  {
    name: kindFilterOf(accountId),
    label: 'Tipo',
    all: 'Tutti',
    options: [
      { value: 'variazione del saldo', label: 'Variazioni del saldo' },
      { value: 'posizione', label: 'Posizioni' },
      { value: 'esecuzione', label: 'Esecuzioni' },
    ],
  },
  {
    name: periodFilterOf(accountId),
    label: 'Periodo',
    all: PERIOD_LABELS[DEFAULT_PERIOD],
    options: WIDER_PERIODS.map((kind) => ({ value: kind, label: PERIOD_LABELS[kind] })),
  },
];

/** The query of the API from the filters of the address: the period becomes the instants it starts from. */
const queryOf = (
  accountId: string,
  values: Readonly<Record<string, string>>,
  now: Date,
): UnattributableQuery => {
  const chosen = values[periodFilterOf(accountId)];
  const kind = WIDER_PERIODS.find((wider) => wider === chosen) ?? DEFAULT_PERIOD;
  const interval = listIntervalOf({ kind, from: '', to: '' }, now);
  return { kind: values[kindFilterOf(accountId)], since: interval.from, until: interval.to };
};

// A change of the balance is money of the account; a position or an execution says its size, in the asset.
const amountOf = (recorded: Unattributable, currency: string): string =>
  recorded.kind === 'variazione del saldo'
    ? `${formatAmount(recorded.amount)} ${currency}`
    : formatAmount(recorded.amount);

const columnsIn = (currency: string): DataTableColumn<Unattributable>[] => [
  { header: 'Rilevato il', cell: (recorded) => formatInstant(recorded.detected_at) },
  { header: 'Tipo', cell: (recorded) => KIND_LABELS[recorded.kind] },
  { header: 'Asset', cell: (recorded) => recorded.asset ?? '—' },
  { header: 'Importo', cell: (recorded) => amountOf(recorded, currency) },
];

const countOf = (total: number): string => (total === 1 ? '1 movimento' : `${total} movimenti`);

const MovementsContent = ({ account }: { readonly account: Account }) => {
  const filters = filtersOf(account.id);
  const { values } = useTableFilters(filters);
  const record = useUnattributable(account.id, queryOf(account.id, values, new Date()));
  if (record.isPending) {
    return <Loading />;
  }
  if (record.data === undefined) {
    return <ErrorMessage error={record.error} />;
  }
  const { pages } = record.data;
  // Every page carries the totals of the whole filter: the last one read is as good as any.
  const totals = pages.reduce<Totals>((_, page) => page, NO_TOTALS);
  const rows = pages.flatMap((page) => page.items);
  return (
    <>
      <p className="text-sm font-medium">
        {`Totale netto delle variazioni: ${formatAmount(totals.net_change)} ${account.currency}`}
      </p>
      <DataTable
        label={TITLE}
        columns={columnsIn(account.currency)}
        rows={rows}
        rowKey={(recorded) => `${recorded.detected_at}-${recorded.kind}-${recorded.asset ?? ''}`}
        empty="Nessun movimento non spiegato nel periodo"
        filtering={{ filters, total: totals.count, countOf }}
      />
      {record.hasNextPage && (
        <CommandButton
          tone="secondary"
          disabled={record.isFetchingNextPage}
          onClick={() => void record.fetchNextPage()}
        >
          Altri
        </CommandButton>
      )}
    </>
  );
};

/**
 * The record of what no flow explains on the account, under its reconciliation, as a portal shows the activity of a
 * resource: the changes of the balance within the threshold and the other cases, newest first, with the net of the
 * changes of the period, the shared filters and the next page on request (R1.6.2, ADR
 * movimenti-non-spiegati-nel-riquadro-del-conto).
 */
export const UnattributableMovements = ({ account }: { readonly account: Account }) => (
  <section
    aria-label={`${TITLE} del conto ${account.name}`}
    className="min-w-0 space-y-2 border-t border-slate-200 pt-3"
  >
    <h3 className="font-semibold">{TITLE}</h3>
    <MovementsContent account={account} />
  </section>
);
