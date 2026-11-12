# ADR 0072 — Il link del bot insieme al codice di collegamento

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.8.1; Bug 163
- Collegate: ADR 0035 (bot Telegram nel worker), ADR 0021 (servizio interno del worker), ADR 0071 (token dalla
  pipeline)

## Contesto

Collegare la chat chiedeva di copiare il codice e incollarlo nella chat del bot. Il proprietario lo trova
scomodo: il codice deve arrivare con un link che con un tocco apre il bot e gli invia il codice. Telegram apre
`https://t.me/<nome del bot>?start=<parametro>` e invia al bot `/start <parametro>`, che il bot già legge. Serve
il nome del bot, che dipende dall'installazione e dal bot creato con BotFather. Il token del bot è solo nel
worker; l'API, che emette il codice, non lo ha.

## Decisione

- **Fonte del nome.** Il worker chiede a Telegram `getMe` con il client del bot e tiene il nome alla prima
  risposta valida; una risposta mancata non si tiene e si richiede alla volta successiva. Il nome non si scrive
  mai nella configurazione.
- **Dal worker all'API.** Il servizio interno del worker espone `GET /bot` (stesso token del worker) con il nome,
  o `null` senza bot. L'API lo chiede con `HttpxWorkerBotIdentityAdapter`, uno per installazione, che tiene il
  nome una volta noto.
- **Risposta.** `POST /telegram/link-code` restituisce `link` accanto a `code` ed `expires_at`. Senza bot attivo,
  o con il worker irraggiungibile, `link` è `null`: il codice si emette comunque e vale inviato a mano. Un worker
  che non risponde si registra nel log, mai un errore all'utente.
- **Messaggi senza codice.** Il solo `/start`, un altro comando o un messaggio vuoto ricevono le istruzioni per il
  collegamento invece di "codice non valido", e non interrogano nessun tenant.

## Alternative scartate

- **Nome del bot in configurazione dell'API.** Un valore in più da tenere allineato al bot vero, per installazione.
- **Token del bot anche all'API.** Allargherebbe chi legge un segreto che oggi ha solo il worker (ADR 0035).
- **Chiedere il nome a ogni richiesta.** Una chiamata a Telegram per ogni codice, senza bisogno: il nome di un bot
  non cambia mentre gira.

## Conseguenze

- Collegare la chat è un tocco sul link.
- Se il bot viene rinominato, API e worker continuano a dare il nome vecchio fino al loro riavvio.
