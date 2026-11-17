import { useState } from 'react';
import { Link } from 'react-router';

import { CommandButton } from '@/components/ui/command-button';
import { paths } from '@/config/paths';

import type { Account } from '../api/get-accounts';

import { RemoveAccount } from './remove-account';
import { ReplaceCredentialsForm } from './replace-credentials-form';

type Action = 'none' | 'replacing' | 'removing';

/** The commands on an account: the replacement of its credentials, its removal (R2.3.1) and its history of the capital
 * (R3.4.2). */
export const AccountActions = ({ account }: { readonly account: Account }) => {
  const [action, setAction] = useState<Action>('none');
  const [replaced, setReplaced] = useState(false);
  const start = (next: Action) => {
    setReplaced(false);
    setAction(next);
  };
  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <CommandButton tone="secondary" onClick={() => start('replacing')}>
          Sostituisci le credenziali
        </CommandButton>
        <CommandButton tone="destructive" onClick={() => start('removing')}>
          Rimuovi
        </CommandButton>
        <Link
          to={paths.accountCapital.getHref(account.id)}
          className="rounded border border-slate-300 px-3 py-1.5 text-blue-800"
        >
          Storico del capitale
        </Link>
      </div>
      {action === 'replacing' && (
        <ReplaceCredentialsForm
          account={account}
          onReplaced={() => {
            setAction('none');
            setReplaced(true);
          }}
          onCancel={() => setAction('none')}
        />
      )}
      {action === 'removing' && (
        <RemoveAccount account={account} onCancel={() => setAction('none')} />
      )}
      {replaced && (
        <p role="status" className="text-green-800">
          Credenziali del conto {account.name} sostituite
        </p>
      )}
    </div>
  );
};
