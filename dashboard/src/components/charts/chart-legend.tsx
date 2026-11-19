import type { ReactElement } from 'react';

// The marks of the charts are drawn around the origin, within this many pixels of it.
const MARK_REACH = 8;

export type LegendEntry = {
  /** The mark the chart draws, as the chart draws it, around the origin. */
  readonly mark: ReactElement;
  readonly label: string;
};

/**
 * The legend below a chart: each entry shows the mark of the chart beside its name, so a mark is not told by its colour
 * alone. The entries wrap on more rows on a phone and stay on one row on a desktop when they fit (ADR
 * legenda-condivisa-dei-grafici).
 */
export const ChartLegend = ({ entries }: { readonly entries: readonly LegendEntry[] }) => (
  <ul aria-label="Legenda" className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
    {entries.map(({ mark, label }) => (
      <li key={label} className="flex items-center gap-1.5">
        <svg
          role="img"
          aria-hidden="true"
          width={2 * MARK_REACH}
          height={2 * MARK_REACH}
          viewBox={`${-MARK_REACH} ${-MARK_REACH} ${2 * MARK_REACH} ${2 * MARK_REACH}`}
          className="shrink-0 overflow-visible"
        >
          {mark}
        </svg>
        {label}
      </li>
    ))}
  </ul>
);
