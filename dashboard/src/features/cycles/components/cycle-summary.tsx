import { formatInstant } from '@/utils/format-instant';

import type { Cycle } from '../api/get-cycle';

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
    <dd>{children}</dd>
  </div>
);

/** When the cycle was planned and started, how it ended, what the model cost and the steps it ran (R1.7.1). */
export const CycleSummaryView = ({ cycle }: { cycle: Cycle }) => (
  <section
    aria-labelledby="cycle-summary"
    className="space-y-3 rounded border border-slate-200 bg-white p-4"
  >
    <h2 id="cycle-summary" className="text-lg font-semibold">
      Riepilogo del ciclo
    </h2>
    <dl className="space-y-1 text-sm">
      <Term term="Pianificato">{formatInstant(cycle.planned_at)}</Term>
      <Term term="Avviato">{startOf(cycle)}</Term>
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
  </section>
);
