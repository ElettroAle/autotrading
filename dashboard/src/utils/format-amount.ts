const THOUSANDS = /\B(?=(\d{3})+(?!\d))/g;
// Italian groups the thousands from five digits on: 3150, but 60.000 (CLDR, as Intl writes the percents below).
const GROUPED_FROM_DIGITS = 5;

const LOCALE = 'it-IT';

const PERCENT = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});
const RATE = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ROUNDED = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 2 });
const ROUNDED_RESULT = new Intl.NumberFormat(LOCALE, {
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});
const USD = new Intl.NumberFormat(LOCALE, { minimumFractionDigits: 2, maximumFractionDigits: 6 });

// Intl formats the decimal text itself, so no digit goes through a binary number on the way (ADR 0018).
type DecimalText = `${number}`;

const decimal = (text: string): DecimalText => text as DecimalText;

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

/** A rate of the API without sign, to two decimals, as a share of the whole reads: 66,67%. */
export const formatRate = (percent: string): string => `${RATE.format(decimal(percent))}%`;

/** An aggregate amount to at most two decimals, where the cents tell enough (R2.2.6). */
export const formatRoundedAmount = (amount: string): string => ROUNDED.format(decimal(amount));

/** An aggregate result to at most two decimals, signed unless even (R2.2.6). */
export const formatRoundedResult = (amount: string): string =>
  ROUNDED_RESULT.format(decimal(amount));

/** A cost in USD: cents always, and the fractions of a cent a model call can cost. */
export const formatUsd = (amount: string): string => USD.format(decimal(amount));
