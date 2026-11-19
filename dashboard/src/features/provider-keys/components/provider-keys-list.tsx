import { useState } from 'react';

import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { ExpiringKeysNotice, ExpiryDateForm, KeyExpiryStatus } from '@/components/ui/key-expiry';
import { Loading } from '@/components/ui/loading';
import { formatInstant } from '@/utils/format-instant';

import { useProviderKeys, type ProviderKey } from '../api/get-provider-keys';
import { useRemoveProviderKey } from '../api/remove-provider-key';
import { useSetProviderKeyExpiry } from '../api/set-provider-key-expiry';

import { ReplaceProviderKeyForm } from './replace-provider-key-form';

type Action = 'none' | 'replacing' | 'removing' | 'dating';

/** What the user is doing on one key of the list: the notice at the head of the page opens a replacement too. */
type Chosen = { readonly provider: string; readonly action: Action; readonly replaced: boolean };

const NOTHING_CHOSEN: Chosen = { provider: '', action: 'none', replaced: false };

const READ_BY = 'dal fornitore';

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

const ProviderKeyExpiryForm = ({
  providerKey,
  onDone,
}: {
  readonly providerKey: ProviderKey;
  readonly onDone: () => void;
}) => {
  const setting = useSetProviderKeyExpiry();
  return (
    <ExpiryDateForm
      subject={providerKey.provider}
      current={providerKey.expiry?.expires_on}
      pending={setting.isPending}
      error={setting.error}
      onSave={(expiresOn) =>
        setting.mutate({ provider: providerKey.provider, expiresOn }, { onSuccess: onDone })
      }
      onCancel={onDone}
    />
  );
};

type ProviderKeyItemProps = {
  readonly providerKey: ProviderKey;
  readonly chosen: Chosen;
  readonly onChoose: (chosen: Chosen) => void;
};

const ProviderKeyItem = ({ providerKey, chosen, onChoose }: ProviderKeyItemProps) => {
  const provider = providerKey.provider;
  const action = chosen.provider === provider ? chosen.action : 'none';
  const replaced = chosen.provider === provider && chosen.replaced;
  const start = (next: Action) => onChoose({ provider, action: next, replaced: false });
  const close = () => onChoose(NOTHING_CHOSEN);
  return (
    <li aria-label={provider} className="px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        <div className="flex flex-col">
          <span className="font-medium">{provider}</span>
          <span className="text-sm text-slate-600">
            Registrata il{' '}
            <time aria-label="Data di registrazione" dateTime={providerKey.registered_at}>
              {formatInstant(providerKey.registered_at)}
            </time>
          </span>
          <KeyExpiryStatus expiry={providerKey} readBy={READ_BY} />
        </div>
        <div className="flex flex-wrap justify-end gap-2">
          {providerKey.expiry_editable && (
            <button
              type="button"
              onClick={() => start('dating')}
              className="rounded border border-slate-300 px-3 py-1.5"
            >
              Indica scadenza
            </button>
          )}
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
          onReplaced={() => onChoose({ provider, action: 'none', replaced: true })}
          onCancel={close}
        />
      )}
      {action === 'dating' && <ProviderKeyExpiryForm providerKey={providerKey} onDone={close} />}
      {action === 'removing' && <RemoveProviderKey providerKey={providerKey} onCancel={close} />}
      {replaced && (
        <p role="status" className="mt-1 text-green-800">
          Chiave di {provider} sostituita
        </p>
      )}
    </li>
  );
};

/**
 * The keys of the providers of the tenant: the provider, the instant of registration and the expiry (R2.3.2, R6.2.2);
 * at the head, as long as a key expires within 30 days or expired, the notice with the command to replace it (ADR
 * scadenza-nelle-pagine-chiavi-e-conti).
 */
export const ProviderKeysList = () => {
  const keys = useProviderKeys();
  const [chosen, setChosen] = useState<Chosen>(NOTHING_CHOSEN);
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
    <>
      <ExpiringKeysNotice
        keys={keys.data.map((providerKey) => ({
          name: providerKey.provider,
          expiry: providerKey,
          renewal: (
            <button
              type="button"
              onClick={() =>
                setChosen({ provider: providerKey.provider, action: 'replacing', replaced: false })
              }
              className="rounded border border-amber-400 bg-white px-3 py-1.5"
            >
              Sostituisci la chiave di {providerKey.provider}
            </button>
          ),
        }))}
      />
      <ul
        aria-label="Chiavi dei fornitori IA"
        className="divide-y divide-slate-200 rounded border border-slate-200 bg-white"
      >
        {keys.data.map((providerKey) => (
          <ProviderKeyItem
            key={providerKey.provider}
            providerKey={providerKey}
            chosen={chosen}
            onChoose={setChosen}
          />
        ))}
      </ul>
    </>
  );
};
