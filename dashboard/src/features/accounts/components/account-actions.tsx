import { useState } from 'react';

import type { Account } from '../api/get-accounts';

import { RemoveAccount } from './remove-account';
import { ReplaceCredentialsForm } from './replace-credentials-form';

type Action = 'none' | 'replacing' | 'removing';

/** The commands on an account: the replacement of its credentials and its removal (R2.3.1). */
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
        <button
          type="button"
          onClick={() => start('replacing')}
          className="rounded border border-slate-300 px-3 py-1.5"
        >
          Sostituisci le credenziali
        </button>
        <button
          type="button"
          onClick={() => start('removing')}
          className="rounded border border-red-300 px-3 py-1.5 text-red-800"
        >
          Rimuovi
        </button>
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
