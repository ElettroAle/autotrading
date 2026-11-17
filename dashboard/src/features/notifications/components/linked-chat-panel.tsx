import { useState } from 'react';

import { ErrorMessage } from '@/components/ui/error-message';
import { Loading } from '@/components/ui/loading';

import { useLinkedChat } from '../api/get-linked-chat';
import { useSendTestNotification } from '../api/send-test-notification';
import { useUnlinkChat } from '../api/unlink-chat';

const COMMAND_FAILED = 'Operazione non riuscita';

const TestNotification = () => {
  const test = useSendTestNotification();
  return (
    <div>
      <button
        type="button"
        onClick={() => test.mutate()}
        disabled={test.isPending}
        className="rounded bg-blue-700 px-3 py-1.5 text-white disabled:opacity-50"
      >
        Invia notifica di prova
      </button>
      {test.isSuccess && (
        <p role="status" className="mt-1 text-green-800">
          Notifica di prova inviata
        </p>
      )}
      {test.isError && <ErrorMessage error={test.error} prefix={COMMAND_FAILED} />}
    </div>
  );
};

const UnlinkChat = () => {
  const [confirming, setConfirming] = useState(false);
  const unlink = useUnlinkChat();
  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="rounded border border-slate-300 px-3 py-1.5"
      >
        Scollega la chat
      </button>
    );
  }
  return (
    <div role="group" aria-label="Scollegamento della chat" className="space-y-2">
      <p>Le notifiche dei tuoi flussi smetteranno di arrivare a questa chat.</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => unlink.mutate()}
          disabled={unlink.isPending}
          className="rounded bg-red-700 px-3 py-1.5 text-white disabled:opacity-50"
        >
          Conferma lo scollegamento
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          className="rounded border border-slate-300 px-3 py-1.5"
        >
          Annulla
        </button>
      </div>
      {unlink.isError && <ErrorMessage error={unlink.error} prefix={COMMAND_FAILED} />}
    </div>
  );
};

// The steps as the bot answers a chat that writes it without a code (R1.8.1, R6.4.1).
const LinkSteps = () => (
  <ol aria-label="Come collegare Telegram" className="mt-2 list-inside list-decimal space-y-1">
    <li>Chiedi qui sotto il codice di collegamento: vale una sola volta e per poco tempo.</li>
    <li>
      Invia il codice al bot della piattaforma dalla tua chat Telegram, oppure apri il link che
      compare insieme al codice.
    </li>
    <li>
      Attendi la conferma del bot: da quel momento la chat riceve le notifiche dei tuoi flussi.
    </li>
  </ol>
);

export const LinkedChatPanel = () => {
  const chat = useLinkedChat();
  return (
    <section
      aria-labelledby="linked-chat-title"
      className="rounded border border-slate-200 bg-white p-4"
    >
      <h3 id="linked-chat-title" className="mb-2 text-lg font-semibold">
        Chat
      </h3>
      {chat.isPending && <Loading />}
      {chat.isError && <ErrorMessage error={chat.error} />}
      {chat.isSuccess && chat.data.chat_id === null && (
        <>
          <p role="status">Nessuna chat collegata</p>
          <LinkSteps />
        </>
      )}
      {chat.isSuccess && chat.data.chat_id !== null && (
        <div className="space-y-3">
          <p role="status" aria-label="Chat collegata">
            Chat Telegram {chat.data.chat_id} collegata
          </p>
          <TestNotification />
          <UnlinkChat />
        </div>
      )}
    </section>
  );
};
