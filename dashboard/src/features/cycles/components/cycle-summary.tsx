import { Card } from '@/components/ui/card';
import { DETAIL_VALUE } from '@/components/ui/details-list';
import { formatInstant } from '@/utils/format-instant';

import type { Cycle } from '../api/get-cycle';
import { ON_DEMAND_LABEL } from '../utils/cycle-trigger';

const startOf = (cycle: Cycle): string => {
  if (cycle.started_at === null) {
    return 'mai';
  }
  const started = formatInstant(cycle.started_at);
  return cycle.delay_seconds === null
    ? started
    : `${started} (${cycle.delay_seconds} s di ritardo)`;
};

const costOf = ({ cost }: Cycle): string => {
  if (cost === null) {
    return 'non disponibile';
  }
  const tokens = `${cost.input_tokens} token in ingresso, ${cost.output_tokens} in uscita`;
  return cost.cost_usd === null ? `sconosciuto (${tokens})` : `${cost.cost_usd} USD (${tokens})`;
};

const Term = ({ term, children }: { term: string; children: string }) => (
  <div className="flex gap-2">
    <dt className="font-medium text-slate-600">{term}</dt>
    <dd className={DETAIL_VALUE}>{children}</dd>
  </div>
);

/**
 * When the cycle was planned and started, whether the user asked for it now, how it ended, what the model cost and the
 * steps it ran (R1.7.1, R6.5.2).
 */
export const CycleSummaryView = ({ cycle }: { cycle: Cycle }) => (
  <Card as="section" aria-labelledby="cycle-summary" className="space-y-3">
    <h2 id="cycle-summary" className="text-lg font-semibold">
      Riepilogo del ciclo
    </h2>
    <dl className="space-y-1 text-sm">
      <Term term="Pianificato">{formatInstant(cycle.planned_at)}</Term>
      <Term term="Avviato">{startOf(cycle)}</Term>
      {cycle.trigger === 'on_demand' && <Term term="Avvio">{ON_DEMAND_LABEL}</Term>}
      <Term term="Esito">{cycle.outcome}</Term>
      <Term term="Costo del modello">{costOf(cycle)}</Term>
    </dl>
    {cycle.steps.length > 0 && (
      <ol aria-label="Passi eseguiti" className="list-inside list-decimal text-sm">
        {cycle.steps.map((step) => (
          <li key={step}>{step}</li>
        ))}
      </ol>
    )}
  </Card>
);
