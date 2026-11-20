import { useId, type ReactNode } from 'react';

import { DETAIL_VALUE, DETAILS_GRID } from '@/components/ui/details-list';
import { ErrorMessage } from '@/components/ui/error-message';
import { usePeriod } from '@/components/ui/period-selector/use-period';
import { formatRate, formatRoundedAmount } from '@/utils/format-amount';

import {
  useForecastAccuracy,
  type ForecastAccuracy as Accuracy,
} from '../api/get-forecast-accuracy';

const MINUTES_IN_HOUR = 60;
const MINUTES_IN_DAY = 24 * MINUTES_IN_HOUR;
const MINUTES_IN_WEEK = 7 * MINUTES_IN_DAY;
const NOT_AVAILABLE = 'non disponibile nel periodo';
const SEPARATOR = ' · ';

const counted = (count: number, one: string, many: string): string =>
  `${count} ${count === 1 ? one : many}`;

// The long horizons of the forecast are days and weeks (R5.1.5).
const horizonLabel = (minutes: number): string => {
  if (minutes % MINUTES_IN_WEEK === 0) {
    return counted(minutes / MINUTES_IN_WEEK, 'settimana', 'settimane');
  }
  if (minutes % MINUTES_IN_DAY === 0) {
    return counted(minutes / MINUTES_IN_DAY, 'giorno', 'giorni');
  }
  if (minutes % MINUTES_IN_HOUR !== 0) {
    return counted(minutes, 'minuto', 'minuti');
  }
  return counted(minutes / MINUTES_IN_HOUR, 'ora', 'ore');
};

// The values are the API's: the panel formats them and computes nothing (ADR errore-della-previsione-nella-pagina-del-flusso).
const errorText = (accuracy: Accuracy): string => {
  const {
    mean_absolute_error: absolute,
    mean_percent_error: percent,
    evaluated,
    unevaluable,
  } = accuracy;
  const measured =
    absolute === null || percent === null
      ? [NOT_AVAILABLE]
      : [
          `errore medio ${formatRoundedAmount(absolute)}`,
          formatRate(percent),
          counted(evaluated, 'previsione valutata', 'previsioni valutate'),
        ];
  const missing = unevaluable > 0 ? [counted(unevaluable, 'non valutabile', 'non valutabili')] : [];
  return [...measured, ...missing].join(SEPARATOR);
};

const AccuracyEntry = ({ accuracy }: { accuracy: Accuracy }) => {
  const id = useId();
  return (
    <div className="contents">
      <dt id={id} className="text-slate-600">
        {`${accuracy.asset}${SEPARATOR}${horizonLabel(accuracy.horizon_minutes)}`}
      </dt>
      <dd aria-labelledby={id} className={`${DETAIL_VALUE} font-medium`}>
        {errorText(accuracy)}
      </dd>
    </div>
  );
};

const AccuracyPanel = ({ children }: { children: ReactNode }) => {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="mt-4 rounded border border-slate-200 bg-white p-4"
    >
      <h3 id={titleId} className="mb-2 text-lg font-semibold">
        Errore della previsione
      </h3>
      {children}
    </section>
  );
};

/**
 * The error of the forecasts of the flow over the period chosen on the page, by asset and horizon (R3.6.1); a flow
 * without forecasts has no panel.
 */
export const ForecastAccuracy = ({ flowId }: { flowId: string }) => {
  const [period] = usePeriod();
  const accuracy = useForecastAccuracy(flowId, period);
  if (accuracy.isPending) {
    return null;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (accuracy.data === undefined) {
    return (
      <AccuracyPanel>
        <ErrorMessage error={accuracy.error} />
      </AccuracyPanel>
    );
  }
  if (accuracy.data.forecasts.length === 0) {
    return null;
  }
  return (
    <AccuracyPanel>
      <dl className={DETAILS_GRID}>
        {accuracy.data.forecasts.map((entry) => (
          <AccuracyEntry key={`${entry.asset}-${entry.horizon_minutes}`} accuracy={entry} />
        ))}
      </dl>
    </AccuracyPanel>
  );
};
