import type { ReactNode } from 'react';

import { formatRoundedAmount, formatRoundedResult } from '@/utils/format-amount';
import { gainTone } from '@/utils/gain-tone';

const Total = ({ label, children }: { readonly label: string; readonly children: ReactNode }) => (
  <div className="flex gap-2">
    <dt className="text-slate-600">{label}</dt>
    <dd className="font-medium">{children}</dd>
  </div>
);

type HistoryTotalsProps = { readonly pnl?: string; readonly fees: string };

/**
 * The totals of every row of the search, as the API sums them, not only of the rows loaded (Bug 569): the PnL with
 * the colour of its sign, when the history has one, and the fees.
 */
export const HistoryTotals = ({ pnl, fees }: HistoryTotalsProps) => (
  <dl aria-label="Totali della ricerca" className="mb-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
    {pnl === undefined ? null : (
      <Total label="Totale PnL">
        <span className={gainTone(pnl)}>{formatRoundedResult(pnl)}</span>
      </Total>
    )}
    <Total label="Totale commissioni">{formatRoundedAmount(fees)}</Total>
  </dl>
);
