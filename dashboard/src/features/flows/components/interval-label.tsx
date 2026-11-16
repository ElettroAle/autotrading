import { usePeriodInterval } from '@/components/ui/period-selector/use-period';
import { formatMinute } from '@/utils/format-instant';

/**
 * The interval chosen on the equity curve, said above the tabs with the command that removes it and brings back the
 * period of the menu (R6.4.3, ADR intervallo-trascinando-sull-equity-curve); each end with its date and its time, «16/11
 * 09:15 – 16/11 11:40» (ADR periodo-al-minuto).
 */
export const IntervalLabel = () => {
  const { interval, clearInterval } = usePeriodInterval();
  if (interval === undefined) {
    return null;
  }
  return (
    <p
      aria-label="Intervallo scelto sul grafico"
      className="mb-4 inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 py-1 pr-1 pl-3 text-sm text-blue-900"
    >
      <span>{`${formatMinute(interval.from)} – ${formatMinute(interval.to)}`}</span>
      <button
        type="button"
        onClick={clearInterval}
        aria-label="Togli l'intervallo"
        className="inline-flex size-8 items-center justify-center rounded-full hover:bg-blue-100"
      >
        <span aria-hidden="true">×</span>
      </button>
    </p>
  );
};
