const THOUSANDS = /\B(?=(\d{3})+(?!\d))/g;
// Italian groups the thousands from five digits on: 3150, but 60.000 (CLDR, as Intl writes the percents below).
const GROUPED_FROM_DIGITS = 5;

const PERCENT = new Intl.NumberFormat('it-IT', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});

/**
 * An amount as the API writes it (a decimal string, ADR 0018), in Italian: grouped thousands and decimal comma. The
 * text is rewritten digit for digit, never through a binary number, so no amount loses precision on the screen.
 */
export const formatAmount = (amount: string): string => {
  const negative = amount.startsWith('-');
  const [whole = '', fraction] = (negative ? amount.slice(1) : amount).split('.');
  const grouped = whole.length < GROUPED_FROM_DIGITS ? whole : whole.replace(THOUSANDS, '.');
  return `${negative ? '-' : ''}${fraction === undefined ? grouped : `${grouped},${fraction}`}`;
};

/** An amount with its sign, as a result reads: +12 for a gain, -0,5 for a loss. */
export const formatSignedAmount = (amount: string): string =>
  Number(amount) > 0 ? `+${formatAmount(amount)}` : formatAmount(amount);

/** A percent of the API with its sign, to two decimals: only the display is rounded. */
export const formatPercent = (percent: string): string => `${PERCENT.format(Number(percent))}%`;
