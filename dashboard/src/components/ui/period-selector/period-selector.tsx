import { useId } from 'react';

import { PERIODS, usePeriod, type PeriodKind } from './use-period';

const FIELD = 'rounded border border-slate-300 bg-white px-2 py-1';

/** The period of the panels of a page: the same choice for statistics, equity curve and ranking (ADR 0123). */
export const PeriodSelector = () => {
  const [period, choose] = usePeriod();
  const id = useId();
  return (
    <div className="my-4 flex flex-wrap items-center gap-3">
      <label htmlFor={`${id}-kind`}>Periodo</label>
      <select
        id={`${id}-kind`}
        className={FIELD}
        value={period.kind}
        onChange={(event) => choose({ ...period, kind: event.target.value as PeriodKind })}
      >
        {PERIODS.map(({ kind, label }) => (
          <option key={kind} value={kind}>
            {label}
          </option>
        ))}
      </select>
      {period.kind === 'range' && (
        <>
          <label htmlFor={`${id}-from`}>Dal</label>
          <input
            id={`${id}-from`}
            type="date"
            className={FIELD}
            value={period.from}
            onChange={(event) => choose({ ...period, from: event.target.value })}
          />
          <label htmlFor={`${id}-to`}>Al</label>
          <input
            id={`${id}-to`}
            type="date"
            className={FIELD}
            value={period.to}
            onChange={(event) => choose({ ...period, to: event.target.value })}
          />
        </>
      )}
    </div>
  );
};
