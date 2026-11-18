import { useState } from 'react';
import { useNavigate } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { DangerZone } from '@/components/ui/danger-zone';
import { paths } from '@/config/paths';

import type { Account } from '../api/get-accounts';
import { useAccount } from '../hooks/use-account';

import { RemoveAccount } from './remove-account';
import { ReplaceCredentialsForm } from './replace-credentials-form';

type Replacement = 'closed' | 'open' | 'done';

/** The credentials of the account, replaced with the fields its exchange declares (R2.3.1, R2.3.9). */
const Credentials = ({ account }: { readonly account: Account }) => {
  const [replacement, setReplacement] = useState<Replacement>('closed');
  return (
    <section
      aria-label={`Credenziali del conto ${account.name}`}
      className="space-y-2 rounded border border-slate-200 bg-white p-4"
    >
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
    </section>
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

/**
 * The tab Impostazioni of the page of the account: its credentials, then its removal in the zone of danger (ADR
 * elenco-dei-conti-e-pagina-del-conto). The page has read the account before its tabs show.
 */
export const AccountSettings = ({ accountId }: { readonly accountId: string }) => {
  const account = useAccount(accountId);
  if (account === undefined) {
    return null;
  }
  return (
    <>
      <Credentials account={account} />
      <Removal account={account} />
    </>
  );
};
