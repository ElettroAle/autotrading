// The API writes numbers as decimal text (ADR 0018): Intl formats the text itself, so no digit goes through a float.
const LOCALE = 'it-IT';

const amountFormat = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 2 });
const resultFormat = new Intl.NumberFormat(LOCALE, {
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
});
const percentFormat = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const usdFormat = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 6,
});

type DecimalText = `${number}`;

const decimal = (text: string): DecimalText => text as DecimalText;

/** An amount in Italian, with at most two decimals. */
export const formatAmount = (text: string): string => amountFormat.format(decimal(text));

/** A gain or a loss in Italian, signed unless even. */
export const formatResult = (text: string): string => resultFormat.format(decimal(text));

/** A percentage in Italian with two decimals. */
export const formatPercent = (text: string): string => `${percentFormat.format(decimal(text))}%`;

/** A cost in USD in Italian: cents always, and the fractions of a cent a model call can cost. */
export const formatUsd = (text: string): string => usdFormat.format(decimal(text));
