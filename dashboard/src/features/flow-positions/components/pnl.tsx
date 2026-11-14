import { formatPercent, formatSignedAmount } from '@/utils/format-amount';

const toneOf = (amount: string): string => {
  const value = Number(amount);
  if (value > 0) {
    return 'text-green-700';
  }
  return value < 0 ? 'text-red-700' : 'text-slate-700';
};

/** A result in value, with its sign and, when given, its unit: green for a gain, red for a loss. */
export const PnlAmount = ({ amount, unit }: { amount: string; unit?: string }) => (
  <span className={toneOf(amount)}>
    {unit === undefined ? formatSignedAmount(amount) : `${formatSignedAmount(amount)} ${unit}`}
  </span>
);

/** A result in percent, coloured as its value; a dash when the API has none. */
export const PnlPercent = ({ percent }: { percent: string | null }) =>
  percent === null ? (
    <span>—</span>
  ) : (
    <span className={toneOf(percent)}>{formatPercent(percent)}</span>
  );
