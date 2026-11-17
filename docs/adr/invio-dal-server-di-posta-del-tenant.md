# ADR invio-dal-server-di-posta-del-tenant — Invio delle email dal server di posta del tenant

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.5, Task T3.5.5.2; R3.5.2, R3.5.3
- Collegate: ADR server-di-posta-per-tenant, ADR canale-email-delle-notifiche-con-smtp (sostituita: niente più servizio
  dell'installazione), ADR outbox-delle-integrazioni-esterne-con-procrastinate, ADR permanenza-decisa-dall-errore-base
- Verifica: prova

## Contesto e problema

Con il server per tenant (ADR server-di-posta-per-tenant), l'invio non può più usare un mailer configurato all'avvio
del worker, e la disponibilità del canale non dipende più dall'installazione ma dal tenant. L'email di prova oggi passa
dall'outbox e l'utente non vede se il server rifiuta.

## Fattori decisionali

- R3.5.5: email di prova con esito immediato; le notifiche dal server del loro tenant.
- CLAUDE.md: il caso d'uso orchestra gli adapter; un adapter non riceve porte; errori tipizzati con la causa.
- ADR 0007: la password si apre solo nel worker.
- Outbox: le notifiche restano asincrone con ritentativi.

## Decisione

- `MailerPort.send(server: MailServer, password: str, address, subject, text)`: `SmtpMailerAdapter` non ha più
  configurazione; apre una connessione per email verso `server` (TLS implicito per `TLS`, `starttls` per `STARTTLS`,
  contesto TLS verificato) e fa login con utente e password. Un rifiuto di autenticazione (`SMTPAuthenticationError`)
  diventa `MailServerRefusedLoginError` (motivo «il server di posta ha rifiutato l'accesso: controlla utente e
  password»), gli altri errori `EmailNotDeliveredError`, sempre `from error`.
- `DeliverOutboxMessageUseCase`, per un messaggio email: legge il server del tenant del messaggio
  (`MailServerRepositoryPort` legato al tenant), apre la password (`MailPasswordOpenerPort`) e invia. Senza server il
  messaggio fallisce con `MailServerNotConfiguredError` registrato.
- Disponibilità: `NotifyUseCase` e la scelta dei canali considerano il canale email disponibile se il tenant ha un
  server (porta `MailServerRepositoryPort`); l'avviso della scelta dei canali dice «server di posta non configurato».
  Spariscono `MailServicePort`, `SmtpMailServiceAdapter`, `SmtpDisabledMailerAdapter`, `SMTP_*` e il file della
  password dell'installazione, con i loro test e la parte di `deploy/` che li citasse.
- Email di prova sincrona: `SendTestEmailUseCase` gira nel worker e invia subito; l'API la chiede al worker con la sua
  API interna (`adapters/outbound/worker`) e restituisce il rifiuto del server come errore tipizzato (400 per
  credenziali rifiutate, 503 per server non raggiungibile), mostrato nel pannello.
- Le specifiche di R3.5.2 e R3.5.3 si riallineano: «servizio di posta dell'installazione» diventa «server di posta del
  tenant».

## Alternative scartate

- Email di prova dall'outbox: l'utente non vedrebbe il rifiuto del server.
- Mailer creato per tenant nel bootstrap: il bootstrap non decide e non legge dati di tenant.

## Conseguenze

- Il canale email funziona appena l'utente salva il proprio server, senza deploy.
- Una password errata si scopre con la prova; per le notifiche il fallimento si registra e si ritenta.
