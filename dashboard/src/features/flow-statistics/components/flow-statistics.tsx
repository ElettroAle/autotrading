import { useId, type ReactNode } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { usePeriod } from '@/components/ui/period-selector/use-period';
import {
  formatRate,
  formatRoundedAmount,
  formatRoundedResult,
  formatUsd,
} from '@/utils/format-amount';

import { useFlowStatistics, type FlowStatistics as Statistics } from '../api/get-flow-statistics';

const NOT_AVAILABLE = 'non disponibile';

const orNotAvailable = (text: string | null, format: (value: string) => string): string =>
  text === null ? NOT_AVAILABLE : format(text);

const modelCost = ({ model_cost_usd, model_calls_without_cost }: Statistics): string => {
  const cost = `${formatUsd(model_cost_usd)} USD`;
  return model_calls_without_cost === 0
    ? cost
    : `${cost} (${model_calls_without_cost} chiamate senza costo noto)`;
};

const Statistic = ({ label, children }: { label: string; children: ReactNode }) => {
  const id = useId();
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-1">
      <dt id={id} className="text-slate-600">
        {label}
      </dt>
      <dd aria-labelledby={id} className="font-medium">
        {children}
      </dd>
    </div>
  );
};

// The values are the API's: the panel formats them and computes nothing (ADR 0123).
const StatisticsList = ({ statistics }: { statistics: Statistics }) => (
  <dl>
    <Statistic label="Operazioni vinte">{statistics.won}</Statistic>
    <Statistic label="Operazioni perse">{statistics.lost}</Statistic>
    <Statistic label="Win rate">
      {orNotAvailable(statistics.win_rate_percent, formatRate)}
    </Statistic>
    <Statistic label="PnL medio delle vincenti">
      {orNotAvailable(
        statistics.average_winning_pnl,
        (value) => `${formatRoundedResult(value)} USDC`,
      )}
    </Statistic>
    <Statistic label="PnL medio delle perdenti">
      {orNotAvailable(
        statistics.average_losing_pnl,
        (value) => `${formatRoundedResult(value)} USDC`,
      )}
    </Statistic>
    <Statistic label="Commissioni totali">{`${formatRoundedAmount(statistics.total_fees)} USDC`}</Statistic>
    <Statistic label="Numero di operazioni">{statistics.operations}</Statistic>
    <Statistic label="Costo del modello IA">{modelCost(statistics)}</Statistic>
  </dl>
);

const StatisticsContent = ({ flowId }: { flowId: string }) => {
  const [period] = usePeriod();
  const statistics = useFlowStatistics(flowId, period);
  if (statistics.isError) {
    return <ErrorMessage error={statistics.error} />;
  }
  if (statistics.isPending && statistics.fetchStatus === 'idle') {
    return (
      <p className="text-slate-500">Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.</p>
    );
  }
  if (statistics.isPending) {
    return <Loading />;
  }
  return <StatisticsList statistics={statistics.data} />;
};

/** The statistics of the flow over the period chosen on the page (R2.2.6). */
export const FlowStatistics = ({ flowId }: { flowId: string }) => {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="mt-4 rounded border border-slate-200 bg-white p-4"
    >
      <h3 id={titleId} className="mb-2 text-lg font-semibold">
        Statistiche
      </h3>
      <StatisticsContent flowId={flowId} />
    </section>
  );
};
