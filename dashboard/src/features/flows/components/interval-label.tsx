import { usePeriodInterval } from '@/components/ui/period-selector/use-period';

// The days as the user reads them, 10/11/2026, from the days of the address, 2026-11-10.
const dayText = (day: string): string => day.split('-').reverse().join('/');

/**
 * The interval chosen on the equity curve, said above the tabs with the command that removes it and brings back the
 * period of the menu (R6.4.3, ADR intervallo-trascinando-sull-equity-curve).
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
      <span>{`dal ${dayText(interval.from)} al ${dayText(interval.to)}`}</span>
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
