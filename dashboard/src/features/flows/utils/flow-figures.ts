import { formatPercent } from '@/utils/format-amount';

const NOT_AVAILABLE = 'non disponibile';

/** The return the API measured (ADR 0127), with its sign; not available without initial capital. */
export const formatReturn = (percent: string | null): string =>
  percent === null ? NOT_AVAILABLE : formatPercent(percent);
