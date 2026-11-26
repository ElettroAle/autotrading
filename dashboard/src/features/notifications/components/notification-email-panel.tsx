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

// The outcome beside the command, the reason of a refusal of the mail server among them (R3.5.5).
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
      {test.isError && <ErrorMessage error={test.error} prefix="Email di prova non inviata" />}
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
// indirizzo-email-nelle-impostazioni-delle-notifiche). Without a mail server the step waits for the first one (ADR
// pagina-notifiche-a-schede).
const AddressForm = ({
  address,
  disabled,
}: {
  readonly address: string | null;
  readonly disabled: boolean;
}) => {
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
      <fieldset disabled={disabled} className="space-y-3">
        {/* The email keyboard on a phone; the form itself is judged by the API. */}
        <InputField
          label="Indirizzo email"
          info="Indirizzo a cui arrivano le notifiche via email. Un indirizzo email. Obbligatorio; per non ricevere più email si rimuove l'indirizzo."
          type="email"
          autoComplete="email"
          error={errors.address}
          {...register('address')}
        />
        <CommandButton tone="primary" type="submit" disabled={save.isPending}>
          Salva
        </CommandButton>
      </fieldset>
    </form>
  );
};

type NotificationEmailPanelProps = {
  /** Whether the user saved a mail server: without one no email leaves (R3.5.5). */
  readonly serverConfigured: boolean;
};

/**
 * The address of the notifications by email, the second step of the channel: indicated, changed and removed, with a
 * test email from the mail server of the user (R3.5.2, R3.5.5).
 */
export const NotificationEmailPanel = ({ serverConfigured }: NotificationEmailPanelProps) => {
  const email = useNotificationEmail();
  return (
    <section aria-labelledby="notification-email-title" className="space-y-3">
      <h3 id="notification-email-title" className="text-lg font-semibold">
        2. Indirizzo delle notifiche
      </h3>
      {email.isPending && <Loading />}
      {email.isError && <ErrorMessage error={email.error} />}
      {email.isSuccess && (
        <div className="space-y-3">
          {!serverConfigured && (
            <p role="status" className="text-amber-800">
              Configura prima il server di posta
            </p>
          )}
          {email.data.address === null ? (
            <p role="status">Nessun indirizzo email indicato</p>
          ) : (
            <p role="status" aria-label="Indirizzo delle notifiche">
              Le notifiche arrivano anche a {email.data.address}
            </p>
          )}
          <AddressForm
            key={email.data.address ?? ''}
            address={email.data.address}
            disabled={!serverConfigured}
          />
          {email.data.address !== null && (
            <div className="flex flex-col gap-3 sm:flex-row">
              {serverConfigured && <TestEmail />}
              <RemoveAddress />
            </div>
          )}
        </div>
      )}
    </section>
  );
};
