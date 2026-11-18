const EVEN = /^-?0*(\.0*)?$/;

/**
 * The colour of a result as the API writes it (a decimal string, ADR 0018): green for a gain, red for a loss, grey when
 * even or not given (R2.2.2). Read from the text, never through a binary number.
 */
export const gainTone = (value: string | null): string => {
  if (value === null || EVEN.test(value)) {
    return 'text-slate-700';
  }
  return value.startsWith('-') ? 'text-red-700' : 'text-green-700';
};
