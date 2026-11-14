import { formatPercent } from '@/utils/format-amount';

const isZero = (decimal: string): boolean => /^-?0*(\.0*)?$/.test(decimal);

export type ReturnTone = 'positive' | 'negative' | 'neutral';

const NOT_AVAILABLE = 'non disponibile';

/** The return the API measured (ADR 0127), with its sign; not available without initial capital. */
export const formatReturn = (percent: string | null): string =>
  percent === null ? NOT_AVAILABLE : formatPercent(percent);

/** A gain shows in green and a loss in red (R2.2.2). */
export const returnTone = (percent: string | null): ReturnTone => {
  if (percent === null || isZero(percent)) {
    return 'neutral';
  }
  return percent.startsWith('-') ? 'negative' : 'positive';
};
