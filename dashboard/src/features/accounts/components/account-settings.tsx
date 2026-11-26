import { useState } from 'react';
import { useNavigate } from 'react-router';

import { Card } from '@/components/ui/card';
import { CommandButton } from '@/components/ui/command-button';
import { DangerZone } from '@/components/ui/danger-zone';
import { paths } from '@/config/paths';
import { useSupportedExchanges } from '@/hooks/use-supported-exchanges';

import type { Account } from '../api/get-accounts';
import { useAccount } from '../hooks/use-account';

import { MaxDirectionExposureForm } from './max-direction-exposure-form';
import { RemoveAccount } from './remove-account';
import { ReplaceCredentialsForm } from './replace-credentials-form';
import { VirtualBalanceForm } from './virtual-balance-form';

type Replacement = 'closed' | 'open' | 'done';

/** The credentials of the account, replaced with the fields its exchange declares (R2.3.1, R2.3.9). */
const Credentials = ({ account }: { readonly account: Account }) => {
  const [replacement, setReplacement] = useState<Replacement>('closed');
  return (
    <Card as="section" aria-label={`Credenziali del conto ${account.name}`} className="space-y-2">
      <h2 className="text-lg font-semibold">Credenziali</h2>
      {replacement === 'open' ? (
        <ReplaceCredentialsForm
          account={account}
          onReplaced={() => setReplacement('done')}
          onCancel={() => setReplacement('closed')}
        />
      ) : (
        <CommandButton tone="secondary" onClick={() => setReplacement('open')}>
          Sostituisci le credenziali
        </CommandButton>
      )}
      {replacement === 'done' && (
        <p role="status" className="text-green-800">
          Credenziali del conto {account.name} sostituite
        </p>
      )}
    </Card>
  );
};

/** The removal of the account, alone at the bottom of the page; once done, the page leads back to the accounts. */
const Removal = ({ account }: { readonly account: Account }) => {
  const [asked, setAsked] = useState(false);
  const navigate = useNavigate();
  return (
    <DangerZone title="Zona pericolosa">
      <CommandButton tone="destructive" onClick={() => setAsked(true)}>
        Rimuovi
      </CommandButton>
      {asked && (
        <RemoveAccount
          account={account}
          onCancel={() => setAsked(false)}
          onRemoved={() => void navigate(paths.accounts.getHref())}
        />
      )}
    </DangerZone>
  );
};

/** Whether the exchange of the account holds a virtual balance, as the API lists it (R6.3.2). */
const useHoldsVirtualBalance = (account: Account | undefined): boolean => {
  const exchanges = useSupportedExchanges();
  return (
    exchanges.data?.some(
      (exchange) => exchange.name === account?.exchange && exchange.virtual_balance,
    ) ?? false
  );
};

/**
 * The tab Impostazioni of the page of the account: its credentials, or the virtual balance of an exchange that holds
 * one and asks no credentials (R6.3.2), the limit of the exposure of its flows on one side (R5.5.5, ADR
 * esposizione-del-conto-nella-dashboard), then its removal in the zone of danger (ADR
 * elenco-dei-conti-e-pagina-del-conto). The page has read the account before its tabs show.
 */
export const AccountSettings = ({ accountId }: { readonly accountId: string }) => {
  const account = useAccount(accountId);
  const virtual = useHoldsVirtualBalance(account);
  if (account === undefined) {
    return null;
  }
  return (
    <>
      {virtual ? <VirtualBalanceForm account={account} /> : <Credentials account={account} />}
      <MaxDirectionExposureForm account={account} />
      <Removal account={account} />
    </>
  );
};
