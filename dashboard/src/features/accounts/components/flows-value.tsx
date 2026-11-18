import { formatAmount, formatSignedAmount } from '@/utils/format-amount';
import { gainTone } from '@/utils/gain-tone';

import type { Account } from '../api/get-accounts';
import { useFlowsValue, useFreeCapital } from '../api/get-free-capital';

import { ExchangeAmount } from './exchange-amount';

// The capital allocated comes with the account, so it stays when the exchange does not answer; the result does not.
const Breakdown = ({ account }: { readonly account: Account }) => {
  const result = useFreeCapital(account.id).data?.flows_result;
  return (
    <dl className="text-sm text-slate-600">
      <div className="inline">
        <dt className="inline">capitale allocato</dt>{' '}
        <dd aria-label="capitale allocato" className="inline">
          {formatAmount(account.allocated_capital)}
        </dd>
      </div>
      {result !== undefined && (
        <>
          {' '}
          <div className="inline">
            <dt className="inline">
              <span aria-hidden="true">+ </span>risultato
            </dt>{' '}
            <dd aria-label="risultato" className={`inline ${gainTone(result)}`}>
              {formatSignedAmount(result)}
            </dd>
          </div>
        </>
      )}
    </dl>
  );
};

/**
 * The value of the flows of the account, with the capital allocated to them and their result under it, as the API
 * gives them: the balance reads as the value of the flows plus the free capital (Bug 601, ADR
 * scomposizione-del-saldo-nel-riquadro-del-conto).
 */
export const FlowsValue = ({ account }: { readonly account: Account }) => (
  <>
    <div>
      <ExchangeAmount
        reading={useFlowsValue(account.id)}
        unavailable="Valore dei flussi non disponibile"
      />
    </div>
    <Breakdown account={account} />
  </>
);
