import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';

import { CommandButton } from '@/components/ui/command-button';
import { ConfirmationDialog } from '@/components/ui/confirmation-dialog';
import { ErrorMessage } from '@/components/ui/error-message';
import { FormAlert, InputField, SecretField } from '@/components/ui/form/input-field';
import { SelectField } from '@/components/ui/form/select-field';
import { Loading } from '@/components/ui/loading';
import { showRefusal } from '@/lib/form-errors';

import { SECURITIES, useMailServer, type MailServer } from '../api/get-mail-server';
import { useRemoveMailServer } from '../api/remove-mail-server';
import {
  mailServerInputSchema,
  useSetMailServer,
  type MailServerInput,
} from '../api/set-mail-server';

// The fields of the form by the names the API gives them in its refusals.
const FIELDS = ['host', 'port', 'security', 'username', 'password', 'sender'] as const;
const SUBMISSION_PORT = '587';
const SECURITY_CHOICES = SECURITIES.map((security) => ({ value: security, label: security }));

const isField = (field: string): field is (typeof FIELDS)[number] =>
  FIELDS.some((name) => name === field);

/** The one line that sums up a saved server: the password never shows, only that it is saved. */
export const summaryOf = (server: MailServer): string =>
  [
    `${server.host}:${server.port}`,
    server.security,
    server.username,
    server.password_saved ? 'password salvata' : 'password mancante',
  ].join(' · ');

const valuesOf = (server: MailServer | null): MailServerInput =>
  server === null
    ? {
        host: '',
        port: SUBMISSION_PORT,
        security: 'STARTTLS',
        username: '',
        password: '',
        sender: '',
      }
    : { ...server, port: String(server.port), password: '' };

type MailServerFormProps = {
  readonly server: MailServer | null;
  readonly onDone: () => void;
};

// The technical fields show only while the server is configured (tech-dashboard.md, §Pagine di impostazioni).
const MailServerForm = ({ server, onDone }: MailServerFormProps) => {
  const save = useSetMailServer();
  const {
    register,
    handleSubmit,
    setError,
    resetField,
    formState: { errors },
  } = useForm<MailServerInput>({
    resolver: zodResolver(mailServerInputSchema),
    defaultValues: valuesOf(server),
  });

  const onSubmit = handleSubmit((input) =>
    save.mutate(input, {
      onSuccess: onDone,
      onError: (error) => {
        resetField('password');
        showRefusal(error, setError, (field) => (isField(field) ? field : undefined));
      },
    }),
  );

  return (
    <form
      aria-label="Server di posta"
      onSubmit={(event) => void onSubmit(event)}
      noValidate
      className="space-y-3"
    >
      <p className="text-sm text-slate-600">
        Gmail: smtp.gmail.com · 587 · STARTTLS · password per le app
      </p>
      <FormAlert error={errors.root?.server} />
      <InputField label="Server" autoComplete="off" error={errors.host} {...register('host')} />
      <InputField label="Porta" inputMode="numeric" error={errors.port} {...register('port')} />
      <SelectField
        label="Sicurezza"
        placeholder="Scegli la sicurezza"
        choices={SECURITY_CHOICES}
        error={errors.security}
        {...register('security')}
      />
      <InputField
        label="Utente"
        autoComplete="off"
        error={errors.username}
        {...register('username')}
      />
      {/* A saved password never comes back: an empty field keeps it (ADR server-di-posta-per-tenant). */}
      <SecretField
        label={server === null ? 'Password' : 'Password (vuota per conservare quella salvata)'}
        error={errors.password}
        {...register('password')}
      />
      <InputField
        label="Mittente (se vuoto, l'utente)"
        type="email"
        autoComplete="off"
        error={errors.sender}
        {...register('sender')}
      />
      <div className="flex gap-2">
        <CommandButton tone="primary" type="submit" disabled={save.isPending}>
          Salva il server
        </CommandButton>
        {server !== null && (
          <CommandButton tone="secondary" onClick={onDone}>
            Annulla
          </CommandButton>
        )}
      </div>
    </form>
  );
};

const RemoveMailServer = ({ onCancel }: { readonly onCancel: () => void }) => {
  const remove = useRemoveMailServer();
  return (
    <ConfirmationDialog
      title="Rimozione del server di posta"
      confirmLabel="Conferma la rimozione"
      onConfirm={() => remove.mutate()}
      onCancel={onCancel}
      pending={remove.isPending}
      error={remove.error}
    >
      Le email delle notifiche non partiranno più finché non salvi un altro server di posta.
    </ConfirmationDialog>
  );
};

type SavedMailServerProps = { readonly server: MailServer; readonly onEdit: () => void };

const SavedMailServer = ({ server, onEdit }: SavedMailServerProps) => {
  const [removing, setRemoving] = useState(false);
  return (
    <div className="space-y-3">
      <p aria-label="Server di posta salvato">{summaryOf(server)}</p>
      <div className="flex gap-2">
        <CommandButton tone="secondary" onClick={onEdit}>
          Modifica
        </CommandButton>
        <CommandButton tone="destructive" onClick={() => setRemoving(true)}>
          Rimuovi
        </CommandButton>
      </div>
      {removing && <RemoveMailServer onCancel={() => setRemoving(false)} />}
    </div>
  );
};

/**
 * The mail server the emails of the user leave from (R3.5.5): its form while it is configured, then one line with
 * Modifica and Rimuovi (ADR pagina-notifiche-a-schede).
 */
export const MailServerPanel = () => {
  const server = useMailServer();
  const [editing, setEditing] = useState(false);
  return (
    <section aria-labelledby="mail-server-title" className="space-y-3">
      <h3 id="mail-server-title" className="text-lg font-semibold">
        1. Server di posta
      </h3>
      {server.isPending && <Loading />}
      {server.isError && <ErrorMessage error={server.error} />}
      {server.isSuccess && (server.data === null || editing) && (
        <MailServerForm server={server.data} onDone={() => setEditing(false)} />
      )}
      {server.isSuccess && server.data !== null && !editing && (
        <SavedMailServer server={server.data} onEdit={() => setEditing(true)} />
      )}
    </section>
  );
};
