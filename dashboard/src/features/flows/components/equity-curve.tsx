import { useState } from 'react';

import { EquityChart } from '@/components/charts/equity-chart';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useFlowEquity, type EquityPeriod } from '../api/get-flow-equity';

type PeriodKind = EquityPeriod['kind'];

const PERIODS: ReadonlyArray<readonly [PeriodKind, string]> = [
  ['lifetime', 'Tutta la vita'],
  ['7d', '7 giorni'],
  ['30d', '30 giorni'],
  ['range', 'Intervallo'],
];

const DAY = 24 * 60 * 60 * 1000;

/** The days the user picks, from the start of the first to the end of the last, in the time of the browser. */
const rangeOf = (first: string, last: string): EquityPeriod | undefined => {
  if (first === '' || last === '') {
    return undefined;
  }
  const start = new Date(`${first}T00:00:00`);
  const end = new Date(new Date(`${last}T00:00:00`).getTime() + DAY);
  return start < end ? { kind: 'range', start, end } : undefined;
};

const periodOf = (kind: PeriodKind, first: string, last: string): EquityPeriod | undefined =>
  kind === 'range' ? rangeOf(first, last) : { kind };

const EquityPoints = ({ flowId, period }: { flowId: string; period: EquityPeriod }) => {
  const equity = useFlowEquity(flowId, period);
  if (equity.isPending) {
    return <Loading />;
  }
  if (equity.isError) {
    return <ErrorMessage error={equity.error} />;
  }
  if (equity.data.points.length > 0) {
    return <EquityChart points={equity.data.points} baseline={equity.data.initialCapital} />;
  }
  return (
    <p className="text-slate-600">
      {period.kind === 'lifetime'
        ? 'Nessun ciclo ancora eseguito'
        : 'Nessun ciclo nel periodo scelto'}
    </p>
  );
};

/** The equity curve of the flow, with the period the user chooses: the whole life of the flow by default (R2.2.3). */
export const EquityCurve = ({ flowId }: { flowId: string }) => {
  const [kind, setKind] = useState<PeriodKind>('lifetime');
  const [first, setFirst] = useState('');
  const [last, setLast] = useState('');
  const period = periodOf(kind, first, last);
  return (
    <section
      aria-labelledby="equity-curve"
      className="mt-4 rounded border border-slate-200 bg-white p-4"
    >
      <div className="mb-3 flex flex-wrap items-end gap-4">
        <h3 id="equity-curve" className="text-lg font-semibold">
          Equity curve
        </h3>
        <label className="flex flex-col text-sm">
          Periodo
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value as PeriodKind)}
            className="rounded border border-slate-300 px-2 py-1"
          >
            {PERIODS.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {kind === 'range' && (
          <>
            <label className="flex flex-col text-sm">
              Dal
              <input
                type="date"
                value={first}
                onChange={(event) => setFirst(event.target.value)}
                className="rounded border border-slate-300 px-2 py-1"
              />
            </label>
            <label className="flex flex-col text-sm">
              Al
              <input
                type="date"
                value={last}
                onChange={(event) => setLast(event.target.value)}
                className="rounded border border-slate-300 px-2 py-1"
              />
            </label>
          </>
        )}
      </div>
      {period === undefined ? (
        <p className="text-slate-600">
          Scegli il primo e l&apos;ultimo giorno dell&apos;intervallo.
        </p>
      ) : (
        <EquityPoints flowId={flowId} period={period} />
      )}
    </section>
  );
};
