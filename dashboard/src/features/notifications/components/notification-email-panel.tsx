import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';

import { CommandButton } from '@/components/ui/command-button';
import { ErrorMessage } from '@/components/ui/error-message';
import { InputField } from '@/components/ui/form/input-field';
import { Loading } from '@/components/ui/loading';
import { SessionExpiredError } from '@/lib/auth';

import { useNotificationEmail } from '../api/get-notification-email';
import { useRemoveNotificationEmail } from '../api/remove-notification-email';
import { useSendTestEmail } from '../api/send-test-email';
import {
  notificationEmailInputSchema,
  useSetNotificationEmail,
  type NotificationEmailInput,
} from '../api/set-notification-email';

const COMMAND_FAILED = 'Operazione non riuscita';

const TestEmail = () => {
  const test = useSendTestEmail();
  return (
    <div>
      <CommandButton tone="secondary" onClick={() => test.mutate()} disabled={test.isPending}>
        Invia email di prova
      </CommandButton>
      {test.isSuccess && (
        <p role="status" className="mt-1 text-green-800">
          Email di prova inviata
        </p>
      )}
      {test.isError && <ErrorMessage error={test.error} prefix={COMMAND_FAILED} />}
    </div>
  );
};

const RemoveAddress = () => {
  const remove = useRemoveNotificationEmail();
  return (
    <div>
      <CommandButton tone="secondary" onClick={() => remove.mutate()} disabled={remove.isPending}>
        Togli
      </CommandButton>
      {remove.isError && <ErrorMessage error={remove.error} prefix={COMMAND_FAILED} />}
    </div>
  );
};

// The field is the only one of the form: every refusal of the API concerns it (ADR
// indirizzo-email-nelle-impostazioni-delle-notifiche).
const AddressForm = ({ address }: { readonly address: string | null }) => {
  const save = useSetNotificationEmail();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<NotificationEmailInput>({
    resolver: zodResolver(notificationEmailInputSchema),
    defaultValues: { address: address ?? '' },
  });

  const onSubmit = handleSubmit((input) => {
    save.mutate(input, {
      onError: (error) => {
        if (!(error instanceof SessionExpiredError)) {
          setError('address', { type: 'server', message: error.message });
        }
      },
    });
  });

  return (
    <form onSubmit={(event) => void onSubmit(event)} noValidate className="space-y-3">
      {/* The email keyboard on a phone; the form itself is judged by the API. */}
      <InputField
        label="Indirizzo email"
        type="email"
        autoComplete="email"
        error={errors.address}
        {...register('address')}
      />
      <CommandButton tone="primary" type="submit" disabled={save.isPending}>
        Salva
      </CommandButton>
    </form>
  );
};

/** The address of the notifications by email: indicated, changed and removed, with a test email (R3.5.2). */
export const NotificationEmailPanel = () => {
  const email = useNotificationEmail();
  return (
    <section
      aria-labelledby="notification-email-title"
      className="rounded border border-slate-200 bg-white p-4"
    >
      <h2 id="notification-email-title" className="mb-2 text-xl font-semibold">
        Email
      </h2>
      {email.isPending && <Loading />}
      {email.isError && <ErrorMessage error={email.error} />}
      {email.isSuccess && (
        <div className="space-y-3">
          {email.data.warning !== null && (
            <p role="status" className="text-amber-800">
              {email.data.warning}
            </p>
          )}
          {email.data.address === null ? (
            <p role="status">Nessun indirizzo email indicato</p>
          ) : (
            <p role="status" aria-label="Indirizzo delle notifiche">
              Le notifiche arrivano anche a {email.data.address}
            </p>
          )}
          <AddressForm key={email.data.address ?? ''} address={email.data.address} />
          {email.data.address !== null && (
            <div className="flex flex-col gap-3 sm:flex-row">
              <TestEmail />
              <RemoveAddress />
            </div>
          )}
        </div>
      )}
    </section>
  );
};
