import { ErrorMessage } from '@/components/ui/error-message';

import { useRequestLinkCode, type LinkCode } from '../api/request-link-code';

const timeOfDay = new Intl.DateTimeFormat('it-IT', { hour: '2-digit', minute: '2-digit' });

const IssuedCode = ({ issued }: { issued: LinkCode }) => (
  <div className="mt-3 space-y-1">
    <p>
      Codice:{' '}
      <strong aria-label="Codice di collegamento" className="font-mono text-lg">
        {issued.code}
      </strong>
    </p>
    <p className="text-sm text-slate-600">
      Valido fino alle{' '}
      <time aria-label="Scadenza del codice" dateTime={issued.expires_at}>
        {timeOfDay.format(new Date(issued.expires_at))}
      </time>
      , una sola volta.
    </p>
    {issued.link === null ? (
      <p className="text-sm">Invia il codice al bot della piattaforma dalla tua chat Telegram.</p>
    ) : (
      <a
        href={issued.link}
        target="_blank"
        rel="noreferrer"
        className="font-medium text-blue-800 hover:underline"
      >
        Apri il bot e collega la chat
      </a>
    )}
  </div>
);

export const LinkCodePanel = () => {
  const linkCode = useRequestLinkCode();
  return (
    <section
      aria-labelledby="link-code-title"
      className="rounded border border-slate-200 bg-white p-4"
    >
      <h2 id="link-code-title" className="text-xl font-semibold">
        Collegamento
      </h2>
      <button
        type="button"
        onClick={() => linkCode.mutate()}
        disabled={linkCode.isPending}
        className="mt-2 rounded bg-blue-700 px-3 py-1.5 text-white disabled:opacity-50"
      >
        Chiedi il codice di collegamento
      </button>
      {linkCode.isError && <ErrorMessage error={linkCode.error} prefix="Operazione non riuscita" />}
      {linkCode.isSuccess && <IssuedCode issued={linkCode.data} />}
    </section>
  );
};
