import { formatPercent, formatSignedAmount } from '@/utils/format-amount';
import { gainTone } from '@/utils/gain-tone';

/** A result in value, with its sign and, when given, its unit: green for a gain, red for a loss. */
export const PnlAmount = ({ amount, unit }: { amount: string; unit?: string }) => (
  <span className={gainTone(amount)}>
    {unit === undefined ? formatSignedAmount(amount) : `${formatSignedAmount(amount)} ${unit}`}
  </span>
);

/** A result in percent, coloured as its value; a dash when the API has none. */
export const PnlPercent = ({ percent }: { percent: string | null }) =>
  percent === null ? (
    <span>—</span>
  ) : (
    <span className={gainTone(percent)}>{formatPercent(percent)}</span>
  );
