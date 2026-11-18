import { useState } from 'react';

import { ActionsMenu } from '@/components/ui/actions-menu';

import type { Account } from '../api/get-accounts';

import { RemoveAccount } from './remove-account';
import { ReplaceCredentialsForm } from './replace-credentials-form';

type Action = 'none' | 'replacing' | 'removing';

// The element of the list is a link to the page of the account all over: the menu and the forms of the actions stand
// above that link, so they take the touch themselves. The menu sits in the top right corner, so the values of the
// account keep the whole width of the element on a phone.
const MENU_PLACE = 'absolute top-4 right-4 z-10';
const ABOVE_THE_LINK = 'relative z-10';

/**
 * The menu «Azioni» of an account in the list, with the replacement of its credentials and its removal (R2.3.1), and
 * under the account the form or the confirmation of the action chosen, the same as on the page of the account (ADR
 * elenco-dei-conti-e-pagina-del-conto).
 */
export const AccountActions = ({ account }: { readonly account: Account }) => {
  const [action, setAction] = useState<Action>('none');
  const [replaced, setReplaced] = useState(false);
  const start = (next: Action) => {
    setReplaced(false);
    setAction(next);
  };
  return (
    <>
      <div className={MENU_PLACE}>
        <ActionsMenu
          label={`Azioni del conto ${account.name}`}
          actions={[
            { name: 'Sostituisci le credenziali', onSelect: () => start('replacing') },
            { name: 'Rimuovi', onSelect: () => start('removing'), destructive: true },
          ]}
        />
      </div>
      <div className={ABOVE_THE_LINK}>
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
          <p role="status" className="mt-2 text-green-800">
            Credenziali del conto {account.name} sostituite
          </p>
        )}
      </div>
    </>
  );
};
