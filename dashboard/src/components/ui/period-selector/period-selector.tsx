import { useId } from 'react';

import { FILTER, FILTER_FIELD, FILTER_ROW } from '../filters';

import {
  instantOfLocalInput,
  localInputOf,
  PERIODS,
  useMenuPeriod,
  type PeriodKind,
} from './use-period';

/**
 * The period of the panels of a page: the same choice for statistics, equity curve and ranking (ADR 0123); a range
 * takes the date and time of each end, in the time zone of the browser (ADR periodo-al-minuto).
 */
export const PeriodSelector = () => {
  const [period, choose] = useMenuPeriod();
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
              type="datetime-local"
              className={FILTER_FIELD}
              value={localInputOf(period.from)}
              onChange={(event) =>
                choose({ ...period, from: instantOfLocalInput(event.target.value) })
              }
            />
          </div>
          <div className={FILTER}>
            <label htmlFor={`${id}-to`}>Al</label>
            <input
              id={`${id}-to`}
              type="datetime-local"
              className={FILTER_FIELD}
              value={localInputOf(period.to)}
              onChange={(event) =>
                choose({ ...period, to: instantOfLocalInput(event.target.value) })
              }
            />
          </div>
        </>
      )}
    </div>
  );
};
