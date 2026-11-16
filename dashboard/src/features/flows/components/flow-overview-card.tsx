import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { DETAIL_VALUE } from '@/components/ui/details-list';
import { paths } from '@/config/paths';
import { formatAmount } from '@/utils/format-amount';
import { formatInstant } from '@/utils/format-instant';

import type { FlowOverview } from '../api/get-flow-overviews';
import { formatReturn, returnTone, type ReturnTone } from '../utils/flow-figures';

import { ResultsSummary } from './results-summary';

const STYLE_BY_TONE: Readonly<Record<ReturnTone, string>> = {
  positive: 'text-green-700',
  negative: 'text-red-700',
  neutral: 'text-slate-700',
};

const Fact = ({
  term,
  className = '',
  children,
}: {
  term: string;
  className?: string;
  children: ReactNode;
}) => (
  <div className="flex gap-2">
    <dt className="font-medium text-slate-600">{term}</dt>
    <dd aria-label={term} className={`${DETAIL_VALUE} ${className}`}>
      {children}
    </dd>
  </div>
);

// A draft has no account yet, so no currency nor capital (ADR 0124).
const capitalOf = (amount: string | null, currency: string | null): string =>
  amount === null || currency === null ? 'non disponibile' : `${formatAmount(amount)} ${currency}`;

const lastCycleOf = ({ last_cycle }: FlowOverview): string =>
  last_cycle === null
    ? 'nessuna'
    : `${formatInstant(last_cycle.planned_at)} · ${last_cycle.outcome}`;

/**
 * A flow at a glance: its status, the summary of its results, how its capital is doing, then where and when it runs,
 * in second place (R2.2.2, R6.4.2). The installation is said in the header, not on every card; the summary replaces the
 * row of the outcomes of the last cycles (ADR riepilogo-dei-risultati-nella-dashboard).
 */
export const FlowOverviewCard = ({ flow }: { flow: FlowOverview }) => (
  <article aria-label={flow.name} className="space-y-2">
    <Link to={paths.flow.getHref(flow.id)} className="font-medium text-blue-800 hover:underline">
      {flow.name}
    </Link>
    <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
      <Fact term="Stato">{flow.status}</Fact>
      {flow.pause_reason !== null && <Fact term="Motivo della pausa">{flow.pause_reason}</Fact>}
    </dl>
    {flow.summary !== null && flow.currency !== null && (
      <ResultsSummary flowId={flow.id} currency={flow.currency} summary={flow.summary} />
    )}
    <dl className="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
      <Fact term="Capitale iniziale">{capitalOf(flow.initial_capital, flow.currency)}</Fact>
      <Fact term="Capitale attuale">{capitalOf(flow.current_capital, flow.currency)}</Fact>
      <Fact
        term="Rendimento"
        className={`font-semibold ${STYLE_BY_TONE[returnTone(flow.return_percent)]}`}
      >
        {formatReturn(flow.return_percent)}
      </Fact>
    </dl>
    <dl
      aria-label="Dettagli"
      className="grid gap-x-6 gap-y-1 text-xs text-slate-600 sm:grid-cols-2"
    >
      <Fact term="Conto">{flow.account}</Fact>
      <Fact term="Modello">{flow.model}</Fact>
      <Fact term="Versione">{flow.version}</Fact>
      <Fact term="Ultima esecuzione">{lastCycleOf(flow)}</Fact>
      {flow.next_cycle_at !== null && (
        <Fact term="Prossima esecuzione prevista">{formatInstant(flow.next_cycle_at)}</Fact>
      )}
    </dl>
  </article>
);
