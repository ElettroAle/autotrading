import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { usePeriodSearch } from '@/components/ui/period-selector/use-period';
import { paths } from '@/config/paths';
import { formatGain, formatPercent } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';
import { gainTone } from '@/utils/gain-tone';

import type { ResultsSummary as Summary } from '../api/get-flow-results';

const FAILED_OUTCOME = 'fallito';

const LINK = 'underline-offset-2 hover:underline';

// The failed cycles of the summary are those of the period: their tab keeps it (R6.4.3).
const failedCyclesHref = (flowId: string, periodSearch: string): string => {
  const search = new URLSearchParams(periodSearch);
  search.set('outcome', FAILED_OUTCOME);
  return `${paths.flowCycles.getHref(flowId)}?${search.toString()}`;
};

const gainText = (amount: string, percent: string | null, currency: string): string => {
  const written = `${formatGain(amount)} ${currency}`;
  return percent === null ? written : `${written} · ${formatPercent(percent)}`;
};

const counted = (count: number, one: string, many: string): string =>
  `${count} ${count === 1 ? one : many}`;

const Value = ({
  term,
  className,
  children,
}: {
  term: string;
  className: string;
  children: ReactNode;
}) => (
  <div className="min-w-0">
    <dt className="text-xs font-medium text-slate-600">{term}</dt>
    <dd aria-label={term} className={`text-base font-semibold wrap-anywhere ${className}`}>
      {children}
    </dd>
  </div>
);

const Gain = ({
  term,
  amount,
  percent,
  currency,
}: {
  term: string;
  amount: string;
  percent: string | null;
  currency: string;
}) => (
  <Value term={term} className={gainTone(amount)}>
    {gainText(amount, percent, currency)}
  </Value>
);

// Only failed cycles call for attention: none is said in plain words, without colour nor link (R6.4.2).
const FailedCycles = ({ flowId, count }: { flowId: string; count: number }) => {
  const periodSearch = usePeriodSearch();
  if (count === 0) {
    return (
      <Value term="Cicli falliti" className="text-slate-700">
        nessun errore
      </Value>
    );
  }
  return (
    <Value term="Cicli falliti" className="text-red-700">
      <Link to={failedCyclesHref(flowId, periodSearch)} className={LINK}>
        {counted(count, 'ciclo fallito', 'cicli falliti')}
      </Link>
    </Value>
  );
};

type ResultsSummaryProps = {
  readonly flowId: string;
  readonly currency: string;
  readonly summary: Summary;
  // Only the page of the flow gives it: the card of the list says it among its details (R2.2.2).
  readonly nextCycleAt?: string | null;
  // An archived flow will never run a cycle again: its page says so with a dash (Bug 690).
  readonly archived?: boolean;
};

const NextCycle = ({ at, archived }: { at: string | null | undefined; archived: boolean }) => {
  if (archived) {
    return (
      <Value term="Prossima esecuzione prevista" className="text-slate-900">
        —
      </Value>
    );
  }
  if (at === undefined || at === null) {
    return null;
  }
  return (
    <Value term="Prossima esecuzione prevista" className="text-slate-900">
      {formatInstant(at)}
    </Value>
  );
};

/**
 * How the flow is doing at a glance: the gain read now and the one of the period, open positions and failed cycles, two
 * columns on a phone and four on a wide screen (R6.4.2, ADR riepilogo-dei-risultati-nella-dashboard, ADR
 * nomi-e-istanti-dei-guadagni), then when the next cycle falls, if the flow plans one (R6.4.8, ADR
 * prossima-esecuzione-nel-riepilogo-del-flusso), a dash for an archived flow (ADR
 * pagina-del-flusso-archiviato-in-sola-lettura).
 */
export const ResultsSummary = ({
  flowId,
  currency,
  summary,
  nextCycleAt,
  archived = false,
}: ResultsSummaryProps) => {
  const periodSearch = usePeriodSearch();
  return (
    <section aria-label="Riepilogo dei risultati">
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Gain
          term="Guadagno attuale"
          amount={summary.total_gain}
          percent={summary.total_gain_percent}
          currency={currency}
        />
        <Gain
          term="Guadagno nel periodo"
          amount={summary.period_gain}
          percent={summary.period_gain_percent}
          currency={currency}
        />
        <Value term="Posizioni aperte" className="text-slate-900">
          <Link to={`${paths.flow.getHref(flowId)}${periodSearch}`} className={LINK}>
            {counted(summary.open_positions, 'posizione aperta', 'posizioni aperte')}
          </Link>
        </Value>
        <FailedCycles flowId={flowId} count={summary.failed_cycles} />
        <NextCycle at={nextCycleAt} archived={archived} />
      </dl>
    </section>
  );
};
