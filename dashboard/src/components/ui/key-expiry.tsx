import { useId, type ReactNode } from 'react';
import { useForm } from 'react-hook-form';

import type { KeyExpiry } from '@/types/key-expiry';
import { dayOrNothing, formatDay } from '@/utils/format-day';

import { CommandButton } from './command-button';
import { ErrorMessage } from './error-message';
import { InputField } from './form/input-field';
import { Icon, type IconName } from './icons/icon';

type Look = { readonly tone: string; readonly icon?: IconName };

// Attention and critical carry an icon beside the text: the colour is never the only sign (R6.5.3).
const LOOKS: Readonly<Record<KeyExpiry['expiry_status'], Look>> = {
  unknown: { tone: 'text-slate-500' },
  valid: { tone: 'text-slate-700' },
  expiring: { tone: 'font-semibold text-amber-800', icon: 'triangle-alert' },
  expired: { tone: 'font-semibold text-red-800', icon: 'circle-alert' },
};

const headlineOf = ({ expiry, expiry_status, days_left }: KeyExpiry): string => {
  if (expiry === null || expiry_status === 'unknown') {
    return 'scadenza sconosciuta';
  }
  if (expiry_status === 'expired') {
    return 'scaduta';
  }
  if (expiry_status === 'expiring') {
    return days_left === 1 ? 'scade domani' : `scade tra ${String(days_left)} giorni`;
  }
  return `scade il ${formatDay(expiry.expires_on)}`;
};

/** A key that expires within 30 days or expired has to be renewed, as the API reads it (R6.2.2). */
const needsRenewal = ({ expiry_status }: KeyExpiry): boolean =>
  expiry_status === 'expiring' || expiry_status === 'expired';

type KeyExpiryStatusProps = {
  readonly expiry: KeyExpiry;
  /** Who reads a date not entered by the user, «dall'exchange» or «dal fornitore». */
  readonly readBy: string;
};

/**
 * The expiry of a key beside it: unknown, the day, the days left or expired, as the API reads it today; a date the
 * adapter reads says so (R6.2.2, ADR scadenza-nelle-pagine-chiavi-e-conti).
 */
export const KeyExpiryStatus = ({ expiry, readBy }: KeyExpiryStatusProps) => {
  const look = LOOKS[expiry.expiry_status];
  const day = expiry.expiry?.expires_on;
  return (
    <span
      aria-label="Scadenza della chiave"
      className={`inline-flex flex-wrap items-center gap-1 text-sm ${look.tone}`}
    >
      {look.icon !== undefined && <Icon name={look.icon} />}
      {headlineOf(expiry)}
      {day !== undefined && expiry.expiry_status !== 'valid' && (
        <>
          {' · '}
          <time dateTime={day}>{formatDay(day)}</time>
        </>
      )}
      {expiry.expiry?.source === 'read' && ` · letta ${readBy}`}
    </span>
  );
};

/** A key on the notice: its name, its expiry and the command that renews it. */
export type ExpiringKeyEntry = {
  readonly name: string;
  readonly expiry: KeyExpiry;
  readonly renewal: ReactNode;
};

/**
 * At the head of the pages of the keys and of the accounts, as long as a key expires within 30 days or expired: each
 * such key with the command to renew it (R6.2.2, ADR scadenza-nelle-pagine-chiavi-e-conti).
 */
export const ExpiringKeysNotice = ({ keys }: { readonly keys: readonly ExpiringKeyEntry[] }) => {
  const titleId = useId();
  const expiring = keys.filter((key) => needsRenewal(key.expiry));
  if (expiring.length === 0) {
    return null;
  }
  return (
    <section
      aria-labelledby={titleId}
      className="mb-4 space-y-2 rounded border border-amber-300 bg-amber-50 p-3 text-amber-950"
    >
      <h2 id={titleId} className="flex items-center gap-1 font-semibold">
        <Icon name="triangle-alert" />
        Chiavi da rinnovare
      </h2>
      <ul className="space-y-2">
        {expiring.map((key) => (
          <li key={key.name} className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span>
              Chiave {key.name}: {headlineOf(key.expiry)}
            </span>
            {key.renewal}
          </li>
        ))}
      </ul>
    </section>
  );
};

type ExpiryDateFormProps = {
  /** The key whose expiry the user gives. */
  readonly subject: string;
  /** The day the key expires now, if any. */
  readonly current: string | undefined;
  readonly pending: boolean;
  readonly error: Error | null;
  /** The day entered, or none to forget the date. */
  readonly onSave: (expiresOn: string | null) => void;
  readonly onCancel: () => void;
};

/** The day a key expires, given by the user when the adapter does not read it; no day forgets it (R6.2.2). */
export const ExpiryDateForm = ({
  subject,
  current,
  pending,
  error,
  onSave,
  onCancel,
}: ExpiryDateFormProps) => {
  const { register, handleSubmit } = useForm<{ expires_on: string }>({
    defaultValues: { expires_on: current ?? '' },
  });
  const onSubmit = handleSubmit(({ expires_on }) => onSave(dayOrNothing(expires_on) ?? null));
  return (
    <form
      aria-label={`Scadenza di ${subject}`}
      onSubmit={(event) => void onSubmit(event)}
      noValidate
      className="mt-2 space-y-3"
    >
      {error !== null && <ErrorMessage error={error} prefix="Impossibile salvare la scadenza" />}
      <InputField label="Scadenza" type="date" {...register('expires_on')} />
      <div className="flex gap-2">
        <CommandButton tone="primary" type="submit" disabled={pending}>
          Salva la scadenza
        </CommandButton>
        <CommandButton tone="secondary" onClick={onCancel}>
          Annulla
        </CommandButton>
      </div>
    </form>
  );
};
