// The filters keep their look of a wide screen and stack on a phone (ADR ritocchi-delle-pagine-della-dashboard).

/** The filters of a page: side by side on a wide screen, one under the other on a phone. */
export const FILTER_ROW = 'flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center';

/** A filter: its label above its field on a phone, beside it on a wide screen. */
export const FILTER = 'flex flex-col gap-1 md:flex-row md:items-center md:gap-3';

/** The field of a filter: as wide as the screen on a phone, as wide as its choices on a wide screen. */
export const FILTER_FIELD = 'w-full rounded border border-slate-300 bg-white px-2 py-1 md:w-auto';
