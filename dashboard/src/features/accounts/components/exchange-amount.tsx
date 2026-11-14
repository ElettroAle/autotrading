import type { UseQueryResult } from '@tanstack/react-query';

import { formatAmount } from '@/utils/format-amount';

type Amount = { readonly amount: string; readonly currency: string };

/** An amount the API reads from the exchange: when the exchange does not answer, the cell says so and nothing else. */
export const ExchangeAmount = ({
  reading,
  unavailable,
}: {
  reading: UseQueryResult<Amount>;
  unavailable: string;
}) => {
  if (reading.isPending) {
    return <span className="text-slate-500">…</span>;
  }
  if (reading.isError) {
    return (
      <span title={reading.error.message} className="text-amber-800">
        {unavailable}
      </span>
    );
  }
  return <>{`${formatAmount(reading.data.amount)} ${reading.data.currency}`}</>;
};
