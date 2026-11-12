# ADR 0035 — Bot Telegram nel worker, codici come digest letti per digest, notifiche che non fermano nulla

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.8.1 (Task T1.8.1.1), R1.8.2 (Task T1.8.2.1)

## Contesto

R1.8.1 chiede di collegare una chat Telegram a un tenant con un codice monouso valido 15 minuti, inviato dall'utente
al bot della piattaforma. Un tenant ha al massimo una chat; un nuovo collegamento sostituisce il precedente; la chat
si può scollegare. Un codice scaduto, già usato o inesistente riceve la stessa risposta. R1.8.2 chiede le notifiche
essenziali alla sola chat del tenant; un invio fallito si registra e non fa fallire il ciclo.

Vincoli già decisi (rule `context-notifications.md`, ADR 0015, ADR 0021):

- un solo bot, in long polling: nessuna porta in ingresso;
- il token del bot è un file montato in sola lettura, mai una variabile d'ambiente;
- tutte le tabelle dei dati posseduti hanno la row level security per tenant (`tech-sqlalchemy.md`).

Due problemi aperti:

- Quando il bot riceve un codice, il tenant non è ancora noto. Tutte le letture fuori da `tenancy` passano
  dalla policy per tenant.
- Il token non esiste ancora: lo crea il proprietario con BotFather, a fine lavoro.

## Decisione

- **Contesto `notifications`**, indipendente dagli altri:
  - domain: `LinkCode` (8 caratteri senza 0/O/1/I, digest SHA-256), `PendingLink` (valido fino a 15 minuti
    inclusi, usabile una volta), `LinkedChat`, `ChatId`, `Notification` con i testi esatti di R1.8.2 e `Amount`
    con la virgola decimale;
  - application: `RequestLinkCodeUseCase`, `LinkChatUseCase`, `UnlinkChatUseCase`, `GetLinkedChatUseCase`,
    `NotifyUseCase`, `AnswerBotMessagesUseCase`.
- **Il codice si salva solo come digest.** Il codice in chiaro esiste solo nella risposta all'utente. Ha 40 bit
  casuali e vale 15 minuti, quindi basta uno SHA-256 senza sale.
- **Ricerca per digest sotto row level security.** La tabella `telegram_link_codes` ha due policy:
  - quella per tenant;
  - una seconda solo `SELECT`, che mostra la riga il cui digest coincide con `app.link_code_digest` dichiarato
    nella transazione.

  `SqlAlchemyLinkCodeLookupAdapter` dichiara il digest e legge solo il tenant di quella riga. Chi conosce il
  digest ha il codice, quindi non scopre nulla che non sappia già.

  Il resto del riscatto avviene con le porte legate a quel tenant, come ogni richiesta:
  - lettura del codice, scadenza e uso decisi nel domain;
  - marcatura atomica `used_at IS NULL`: di due chat che mandano lo stesso codice, una sola lo usa;
  - sostituzione della chat con un upsert sulla chiave `tenant_id`.
- **Il bot vive nel worker.** Il worker è il servizio che eseguirà i cicli e quindi invierà le notifiche, e non
  ha porte pubblicate.
  - `BotPolling` è un thread avviato dal lifespan dell'app del worker.
  - Ogni giro chiama `getUpdates` con 30 secondi di long polling e conferma le update precedenti con l'offset.
  - Un giro fallito si registra, attende 5 secondi e riprova.
  - L'API serve solo `POST /telegram/link-code`, `GET /telegram/chat` e `DELETE /telegram/chat`, tutte autenticate,
    e non riceve mai il token.
- **Senza token le notifiche sono spente, non rotte.**
  - `prepare-installation.sh` crea `secrets/telegram_bot_token` vuoto (0400, utente dell'immagine) se manca.
  - La compose lo monta nel worker come `TELEGRAM_BOT_TOKEN_FILE`.
  - Variabile assente, file assente o vuoto: il worker parte senza bot e registra "bot Telegram non configurato:
    notifiche disattivate".
  - Ogni notifica passa da `UnconfiguredMessenger` e diventa un invio fallito registrato.
- **Il token non finisce mai in un log.**
  - Le eccezioni httpx si traducono `from None`, perché il loro testo contiene l'URL e l'URL contiene il token.
    È un'eccezione motivata alla regola di conservare la causa (ADR 0027).
  - Un filtro sul logger `httpx` sostituisce il token nelle righe delle richieste.
- **Notifiche**: `NotifyUseCase` invia alla sola chat del tenant e non fa nulla senza chat collegata. Un invio
  fallito registra "invio della notifica fallito" con tenant e soggetto, senza sollevare.
- Gli scenari di R1.8.2 restano `@wip`: partono tutti da eventi del ciclo (F1.2), che li collegherà a
  `WorkerUseCases.notify`.

## Alternative scartate

- **Tabella dei codici senza row level security.** La regola ammette eccezioni solo per `tenancy`. Inoltre
  esporrebbe al ruolo applicativo i tenant di tutti i codici.
- **Funzione `SECURITY DEFINER`.** Con `FORCE ROW LEVEL SECURITY` anche il proprietario delle tabelle è soggetto
  alle policy, quindi servirebbe un ruolo con `BYPASSRLS`. Le regole di scadenza e uso finirebbero in SQL invece che
  nel domain.
- **Webhook di Telegram.** Richiede una porta pubblica in ingresso, vietata dalla rule.
- **Bot nell'API.** L'API non invia notifiche. Un secondo processo in polling sullo stesso token farebbe
  rispondere 409 a Telegram.
- **Avvio rifiutato senza token.** Bloccherebbe il rilascio fino al passo manuale del proprietario. Il requisito
  stesso ammette flussi che operano senza chat collegata.

## Conseguenze

- Passi del proprietario:
  1. creare il bot con BotFather;
  2. scrivere il token in `/opt/autotrading/secrets/telegram_bot_token` sulla macchina (resta 0400, utente 65532);
  3. riavviare il worker con un nuovo rilascio della pipeline.
- Un solo worker per installazione: due processi in polling sullo stesso token si contendono le update.
- I codici usati o scaduti restano in tabella; una pulizia periodica è lavoro futuro.
