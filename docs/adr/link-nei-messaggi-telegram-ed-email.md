# ADR link-nei-messaggi-telegram-ed-email — Pulsanti sotto il messaggio Telegram e link in fondo all'email

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.6, Task 588
- Collegate: ADR destinazioni-delle-notifiche-nella-dashboard, `.claude/rules/tech-telegram.md`,
  `.claude/rules/tech-smtp.md`, ADR invio-dal-server-di-posta-del-tenant
- Verifica: prova

## Contesto e problema

`adapters/outbound/telegram/bot_api.py` invia `sendMessage` con solo `chat_id` e `text`; il mailer SMTP invia testo
semplice. I link del payload (ADR destinazioni-delle-notifiche-nella-dashboard) devono arrivare all'utente.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): pulsanti sotto il messaggio su Telegram, link testuali in fondo all'email.
- API Bot di Telegram: `reply_markup` con `inline_keyboard` di pulsanti `url`.

## Decisione

- Telegram: se il messaggio ha link, `sendMessage` aggiunge `reply_markup = {"inline_keyboard": [[{text, url}, …]]}`
  (una riga, al più tre pulsanti); senza link il corpo resta com'è.
- Email: il testo termina con una riga vuota e una riga per link («Apri flusso: <url>»), in testo semplice.
- I messaggi già in coda senza `links` si consegnano come prima.
- Prove: unit test dei due adapter (con e senza link) e test di integrazione Telegram esistenti riallineati.

## Alternative scartate

- Link nel testo Telegram: scartata dal proprietario.
- Email HTML: non serve per due link.

## Conseguenze

- Su Telegram la notifica si apre con un tocco.
