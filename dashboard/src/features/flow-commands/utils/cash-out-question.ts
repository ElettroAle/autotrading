import { formatAmount } from '@/utils/format-amount';

type Scaled = { readonly digits: bigint; readonly scale: number };

const scaledOf = (amount: string): Scaled => {
  const [whole = '0', fraction = ''] = amount.split('.');
  const negative = whole.startsWith('-');
  const digits = BigInt(`${whole.replace('-', '')}${fraction}`);
  return { digits: negative ? -digits : digits, scale: fraction.length };
};

const rescaled = ({ digits, scale }: Scaled, to: number): bigint =>
  digits * 10n ** BigInt(to - scale);

const textOf = (digits: bigint, scale: number): string => {
  const negative = digits < 0n;
  const padded = (negative ? -digits : digits).toString().padStart(scale + 1, '0');
  const whole = padded.slice(0, padded.length - scale);
  const fraction = padded.slice(padded.length - scale).replace(/0+$/, '');
  return `${negative ? '-' : ''}${whole}${fraction === '' ? '' : `.${fraction}`}`;
};

/**
 * What the flow would free with its value now and the capital it keeps: two amounts of the API, subtracted digit for
 * digit, never through a binary number (ADR 0018). The amount freed for real is the one the cash-out answers
 * (ADR incasso-dei-profitti-nella-dashboard).
 */
export const estimatedFreed = (totalValue: string, capital: string): string => {
  const value = scaledOf(totalValue);
  const kept = scaledOf(capital);
  const scale = Math.max(value.scale, kept.scale);
  return textOf(rescaled(value, scale) - rescaled(kept, scale), scale);
};

type CashOutQuestion = {
  readonly flowName: string;
  readonly positions: number;
  readonly freed: string;
  readonly currency: string;
};

/** The question the cash-out asks before it closes anything (R3.4.1). */
export const cashOutQuestion = ({
  flowName,
  positions,
  freed,
  currency,
}: CashOutQuestion): string => {
  const amount = `${formatAmount(freed)} ${currency}`;
  if (positions === 0) {
    return `Liberare circa ${amount} da ${flowName}?`;
  }
  const closed = positions === 1 ? '1 posizione' : `${String(positions)} posizioni`;
  return `Chiudere ${closed} di ${flowName} e liberare circa ${amount}?`;
};

/** The flow is worth more than its capital: only then is there a profit to cash out (R3.4.1). */
export const hasProfits = (totalValue: string, capital: string): boolean => {
  const freed = estimatedFreed(totalValue, capital);
  return freed !== '0' && !freed.startsWith('-');
};
