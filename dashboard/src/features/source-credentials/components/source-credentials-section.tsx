import { useState } from 'react';

import { CommandButton } from '@/components/ui/command-button';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { Icon } from '@/components/ui/icons/icon';
import { ExpiryDateForm, KeyExpiryStatus } from '@/components/ui/key-expiry';
import { Loading } from '@/components/ui/loading';
import { formatInstant } from '@/utils/format-instant';

import type { SourceCredentials } from '../api/get-source-credentials';
import { useSourceCredentials } from '../api/get-source-credentials';
import { useRemoveSourceCredentials } from '../api/remove-source-credentials';
import { useSetSourceCredentialsExpiry } from '../api/set-source-credentials-expiry';

import { ConfigureSourceAdapterForm } from './configure-source-adapter-form';

type Action = 'none' | 'configuring' | 'dating' | 'removing';

/** What the user is doing on one adapter of the list. */
type Chosen = { readonly adapter: string; readonly action: Action };

const NOTHING_CHOSEN: Chosen = { adapter: '', action: 'none' };

const READ_BY = 'dal fornitore';

// The state of the credentials in text and icon: the colour is never the only sign (R6.5.3).
const CredentialsState = ({ credentials }: { readonly credentials: SourceCredentials }) => {
  if (credentials.rejected) {
    return (
      <span className="inline-flex items-center gap-1 text-sm font-semibold text-red-800">
        <Icon name="circle-alert" />
        rifiutata dal fornitore
      </span>
    );
  }
  if (credentials.configured) {
    return (
      <span className="inline-flex items-center gap-1 text-sm text-green-800">
        <Icon name="circle-check" />
        configurato
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-sm text-slate-600">
      <Icon name="triangle-alert" />
      non configurato
    </span>
  );
};

const PublicValues = ({ credentials }: { readonly credentials: SourceCredentials }) => {
  const shown = credentials.configuration_fields.filter(
    (field) => !field.secret && credentials.public_values[field.name] !== undefined,
  );
  if (shown.length === 0) {
    return null;
  }
  return (
    <dl className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600">
      {shown.map((field) => (
        <div key={field.name} className="flex gap-1">
          <dt>{field.label}:</dt>
          <dd className="break-all">{credentials.public_values[field.name]}</dd>
        </div>
      ))}
    </dl>
  );
};

const RemoveSourceCredentials = ({
  credentials,
  onCancel,
}: {
  readonly credentials: SourceCredentials;
  readonly onCancel: () => void;
}) => {
  const removal = useRemoveSourceCredentials();
  return (
    <ConfirmationDialog
      confirmLabel="Conferma la rimozione"
      title={`Rimozione delle credenziali di ${credentials.adapter}`}
      onConfirm={() => removal.mutate(credentials.adapter)}
      onCancel={onCancel}
      pending={removal.isPending}
      error={removal.error}
    >
      Le credenziali dell&apos;adapter {credentials.adapter} saranno cancellate: i flussi non
      potranno più attivarlo.
    </ConfirmationDialog>
  );
};

const SourceCredentialsExpiryForm = ({
  credentials,
  onDone,
}: {
  readonly credentials: SourceCredentials;
  readonly onDone: () => void;
}) => {
  const setting = useSetSourceCredentialsExpiry();
  return (
    <ExpiryDateForm
      subject={credentials.adapter}
      current={credentials.expiry?.expires_on}
      pending={setting.isPending}
      error={setting.error}
      onSave={(expiresOn) =>
        setting.mutate({ adapter: credentials.adapter, expiresOn }, { onSuccess: onDone })
      }
      onCancel={onDone}
    />
  );
};

type SourceCredentialsItemProps = {
  readonly credentials: SourceCredentials;
  readonly chosen: Chosen;
  readonly onChoose: (chosen: Chosen) => void;
};

const SourceCredentialsItem = ({ credentials, chosen, onChoose }: SourceCredentialsItemProps) => {
  const adapter = credentials.adapter;
  const action = chosen.adapter === adapter ? chosen.action : 'none';
  const start = (next: Action) => onChoose({ adapter, action: next });
  const close = () => onChoose(NOTHING_CHOSEN);
  return (
    <li aria-label={adapter} className="space-y-2 px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-col gap-1">
          <span className="font-medium break-words">
            {credentials.sources.join(', ')} · {adapter}
          </span>
          <CredentialsState credentials={credentials} />
          <PublicValues credentials={credentials} />
          {credentials.registered_at !== null && (
            <span className="text-sm text-slate-600">
              Salvate il{' '}
              <time aria-label="Data di registrazione" dateTime={credentials.registered_at}>
                {formatInstant(credentials.registered_at)}
              </time>
            </span>
          )}
          {credentials.configured && <KeyExpiryStatus expiry={credentials} readBy={READ_BY} />}
        </div>
        <div className="flex flex-wrap gap-2 sm:justify-end">
          <CommandButton tone="secondary" onClick={() => start('configuring')}>
            {credentials.configured ? 'Sostituisci' : 'Configura'}
          </CommandButton>
          {credentials.configured && credentials.expiry_editable && (
            <CommandButton tone="secondary" onClick={() => start('dating')}>
              Indica scadenza
            </CommandButton>
          )}
          {credentials.configured && (
            <CommandButton tone="destructive" onClick={() => start('removing')}>
              Rimuovi
            </CommandButton>
          )}
        </div>
      </div>
      {action === 'configuring' && (
        <ConfigureSourceAdapterForm credentials={credentials} onSaved={close} onCancel={close} />
      )}
      {action === 'dating' && (
        <SourceCredentialsExpiryForm credentials={credentials} onDone={close} />
      )}
      {action === 'removing' && (
        <RemoveSourceCredentials credentials={credentials} onCancel={close} />
      )}
    </li>
  );
};

/**
 * The adapters of the sources that need configuration, each with its state, its values that are not secret, its expiry
 * and the commands to configure, replace, date and remove its credentials; on a phone each is a card of its own (R4.1.2,
 * ADR sezione-fonti-nella-pagina-chiavi).
 */
export const SourceCredentialsSection = () => {
  const credentials = useSourceCredentials();
  const [chosen, setChosen] = useState<Chosen>(NOTHING_CHOSEN);
  if (credentials.isPending) {
    return <Loading />;
  }
  // A failed rereading keeps the data already read on the page: the warning is the page's (ADR 0119).
  if (credentials.data === undefined) {
    return <ErrorMessage error={credentials.error} />;
  }
  if (credentials.data.length === 0) {
    return <p>Nessun adapter di fonte richiede configurazione.</p>;
  }
  return (
    <ul
      aria-label="Adapter delle fonti"
      className="divide-y divide-slate-200 rounded border border-slate-200 bg-white"
    >
      {credentials.data.map((each) => (
        <SourceCredentialsItem
          key={each.adapter}
          credentials={each}
          chosen={chosen}
          onChoose={setChosen}
        />
      ))}
    </ul>
  );
};
