import { useSearchParams } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { DataTable, type DataTableColumn } from '@/components/ui/data-table';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import {
  PERIODS,
  useListInterval,
  type ListInterval,
  type PeriodKind,
} from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';
import { useTableFilters, type TableFilter } from '@/hooks/use-table-filters';
import { formatInstant } from '@/utils/format-instant';

import { useAlerts, type Alert, type AlertsQuery } from '../api/get-alerts';

import {
  AlertResourceLink,
  AlertSeverityLabel,
  alertStateOf,
  RESOURCE_KIND_LABELS,
  SEVERITY_LABELS,
} from './alert-parts';

const TITLE = 'Avvisi';

// The parameters of the address are those of the API, so a link to the alerts of a resource is the API's own query.
const STATE = 'state';
const SEVERITY = 'severity';
const RESOURCE_KIND = 'resource_kind';
const RESOURCE_ID = 'resource_id';
const PERIOD = 'period';

const WIDER_STATES = ['resolved', 'all'] as const;
const PERIOD_CHOICES: readonly PeriodKind[] = ['24h', '7d', '30d'];
const PERIOD_LABELS = Object.fromEntries(
  PERIODS.map(({ kind, label }) => [kind, label]),
) as Readonly<Record<PeriodKind, string>>;

// The list opens on the open alerts: what still waits for the user (R6.2.3).
const FILTERS: readonly TableFilter[] = [
  {
    name: STATE,
    label: 'Stato',
    all: 'Aperti',
    options: [
      { value: 'resolved', label: 'Risolti' },
      { value: 'all', label: 'Tutti' },
    ],
  },
  {
    name: SEVERITY,
    label: 'Gravità',
    all: 'Tutte',
    options: [
      { value: 'critical', label: SEVERITY_LABELS.critical },
      { value: 'warning', label: SEVERITY_LABELS.warning },
    ],
  },
  {
    name: RESOURCE_KIND,
    label: 'Risorsa',
    all: 'Tutte',
    options: [
      { value: 'account', label: RESOURCE_KIND_LABELS.account },
      { value: 'flow', label: RESOURCE_KIND_LABELS.flow },
      { value: 'key', label: RESOURCE_KIND_LABELS.key },
    ],
  },
  {
    name: PERIOD,
    label: 'Periodo',
    all: PERIOD_LABELS.all,
    options: PERIOD_CHOICES.map((kind) => ({ value: kind, label: PERIOD_LABELS[kind] })),
  },
];

/** The period of the filters of the address; without one the list does not limit the time. */
const periodKindOf = (values: Readonly<Record<string, string>>): PeriodKind =>
  PERIOD_CHOICES.find((kind) => kind === values[PERIOD]) ?? 'all';

/** The query of the API from the filters of the address and the instant the period starts from. */
const queryOf = (
  values: Readonly<Record<string, string>>,
  resourceId: string | null,
  interval: ListInterval,
): AlertsQuery => ({
  state: WIDER_STATES.find((wider) => wider === values[STATE]) ?? 'open',
  severity: values[SEVERITY],
  resourceKind: values[RESOURCE_KIND],
  resourceId: resourceId ?? undefined,
  since: interval.from,
});

const COLUMNS: readonly DataTableColumn<Alert>[] = [
  { header: 'Gravità', cell: (alert) => <AlertSeverityLabel severity={alert.severity} /> },
  { header: 'Avviso', cell: (alert) => alert.title },
  {
    header: 'Risorsa interessata',
    cell: (alert) => <AlertResourceLink resource={alert.resource} />,
  },
  { header: 'Aperto il', cell: (alert) => formatInstant(alert.opened_at) },
  { header: 'Stato', cell: alertStateOf },
];

const countOf = (total: number): string => (total === 1 ? '1 avviso' : `${total} avvisi`);

/**
 * The alerts of the user, newest first, in the shared table with its filters kept in the address: a row opens the
 * detail of the alert (R6.2.3, ADR pagina-avvisi-nella-dashboard). The alerts of one resource come from its link.
 */
export const AlertsList = () => {
  const { values } = useTableFilters(FILTERS);
  const [params] = useSearchParams();
  const interval = useListInterval({ kind: periodKindOf(values), from: '', to: '' });
  const alerts = useAlerts(queryOf(values, params.get(RESOURCE_ID), interval));
  if (alerts.isPending) {
    return <Loading />;
  }
  if (alerts.data === undefined) {
    return <ErrorMessage error={alerts.error} />;
  }
  const { pages } = alerts.data;
  const total = pages.at(-1)?.count ?? 0;
  return (
    <>
      <DataTable
        label={TITLE}
        columns={COLUMNS}
        rows={pages.flatMap((page) => page.items)}
        rowKey={(alert) => alert.id}
        rowHref={(alert) => paths.alert.getHref(alert.id)}
        empty="Nessun avviso aperto"
        filtering={{ filters: FILTERS, total, countOf }}
      />
      {alerts.hasNextPage && (
        <CommandButton
          tone="secondary"
          disabled={alerts.isFetchingNextPage}
          onClick={() => void alerts.fetchNextPage()}
        >
          Altri
        </CommandButton>
      )}
    </>
  );
};
