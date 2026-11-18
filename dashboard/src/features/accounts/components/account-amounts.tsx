import { useAccountBalance } from '../api/get-account-state';
import type { Account } from '../api/get-accounts';
import { useFreeCapital } from '../api/get-free-capital';

import { ExchangeAmount } from './exchange-amount';

/** The balance of the account as the exchange reads it, with the result of the open positions (ADR 0126). */
export const AccountBalance = ({ account }: { readonly account: Account }) => (
  <ExchangeAmount reading={useAccountBalance(account.id)} unavailable="Saldo non disponibile" />
);

/** The capital of the account no flow holds, as the API computes it (R1.1.7). */
export const AccountFreeCapital = ({ account }: { readonly account: Account }) => (
  <ExchangeAmount
    reading={useFreeCapital(account.id)}
    unavailable="Capitale libero non disponibile"
  />
);
