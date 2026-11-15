import { useId } from 'react';

import { FILTER, FILTER_FIELD, FILTER_ROW } from '../filters';

import { PERIODS, usePeriod, type PeriodKind } from './use-period';

/** The period of the panels of a page: the same choice for statistics, equity curve and ranking (ADR 0123). */
export const PeriodSelector = () => {
  const [period, choose] = usePeriod();
  const id = useId();
  return (
    <div className={`my-4 ${FILTER_ROW}`}>
      <div className={FILTER}>
        <label htmlFor={`${id}-kind`}>Periodo</label>
        <select
          id={`${id}-kind`}
          className={FILTER_FIELD}
          value={period.kind}
          onChange={(event) => choose({ ...period, kind: event.target.value as PeriodKind })}
        >
          {PERIODS.map(({ kind, label }) => (
            <option key={kind} value={kind}>
              {label}
            </option>
          ))}
        </select>
      </div>
      {period.kind === 'range' && (
        <>
          <div className={FILTER}>
            <label htmlFor={`${id}-from`}>Dal</label>
            <input
              id={`${id}-from`}
              type="date"
              className={FILTER_FIELD}
              value={period.from}
              onChange={(event) => choose({ ...period, from: event.target.value })}
            />
          </div>
          <div className={FILTER}>
            <label htmlFor={`${id}-to`}>Al</label>
            <input
              id={`${id}-to`}
              type="date"
              className={FILTER_FIELD}
              value={period.to}
              onChange={(event) => choose({ ...period, to: event.target.value })}
            />
          </div>
        </>
      )}
    </div>
  );
};
