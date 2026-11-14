import { useState } from 'react';

import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';
import { formatInstant } from '@/utils/format-instant';

import { useProviderKeys, type ProviderKey } from '../api/get-provider-keys';
import { useRemoveProviderKey } from '../api/remove-provider-key';

import { ReplaceProviderKeyForm } from './replace-provider-key-form';

type Action = 'none' | 'replacing' | 'removing';

const RemoveProviderKey = ({
  providerKey,
  onCancel,
}: {
  readonly providerKey: ProviderKey;
  readonly onCancel: () => void;
}) => {
  const removal = useRemoveProviderKey();
  return (
    <ConfirmationDialog
      confirmLabel="Conferma la rimozione"
      title={`Rimozione della chiave di ${providerKey.provider}`}
      onConfirm={() => removal.mutate(providerKey.provider)}
      onCancel={onCancel}
      pending={removal.isPending}
      error={removal.error}
    >
      La chiave del fornitore {providerKey.provider} sarà cancellata.
    </ConfirmationDialog>
  );
};

const ProviderKeyItem = ({ providerKey }: { readonly providerKey: ProviderKey }) => {
  const [action, setAction] = useState<Action>('none');
  const [replaced, setReplaced] = useState(false);
  const start = (next: Action) => {
    setReplaced(false);
    setAction(next);
  };
  return (
    <li aria-label={providerKey.provider} className="px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col">
          <span className="font-medium">{providerKey.provider}</span>
          <span className="text-sm text-slate-600">
            Registrata il{' '}
            <time aria-label="Data di registrazione" dateTime={providerKey.registered_at}>
              {formatInstant(providerKey.registered_at)}
            </time>
          </span>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => start('replacing')}
            className="rounded border border-slate-300 px-3 py-1.5"
          >
            Sostituisci la chiave
          </button>
          <button
            type="button"
            onClick={() => start('removing')}
            className="rounded border border-red-300 px-3 py-1.5 text-red-800"
          >
            Rimuovi
          </button>
        </div>
      </div>
      {action === 'replacing' && (
        <ReplaceProviderKeyForm
          providerKey={providerKey}
          onReplaced={() => {
            setAction('none');
            setReplaced(true);
          }}
          onCancel={() => setAction('none')}
        />
      )}
      {action === 'removing' && (
        <RemoveProviderKey providerKey={providerKey} onCancel={() => setAction('none')} />
      )}
      {replaced && (
        <p role="status" className="mt-1 text-green-800">
          Chiave di {providerKey.provider} sostituita
        </p>
      )}
    </li>
  );
};

/** The keys of the providers of the tenant: the provider and the instant of registration only (R2.3.2). */
export const ProviderKeysList = () => {
  const keys = useProviderKeys();
  if (keys.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (keys.data === undefined) {
    return <ErrorMessage error={keys.error} />;
  }
  if (keys.data.length === 0) {
    return <p>Non hai ancora chiavi di fornitori IA.</p>;
  }
  return (
    <ul
      aria-label="Chiavi dei fornitori IA"
      className="divide-y divide-slate-200 rounded border border-slate-200 bg-white"
    >
      {keys.data.map((providerKey) => (
        <ProviderKeyItem key={providerKey.provider} providerKey={providerKey} />
      ))}
    </ul>
  );
};
