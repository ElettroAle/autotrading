# ADR 0134 — Notifica di prova Telegram anche dall'API, per la pagina delle notifiche

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.3.6 (Task T2.3.6.1)
- Collegate: R1.8.1 (collegamento e prova dalla chat, `SendTestNotificationUseCase`), ADR 0026 (contesto
  `notifications`), ADR 0116, ADR 0119; API `/telegram/link-code`, `/telegram/chat`

## Contesto e problema

La pagina delle notifiche mostra codice e link del bot, la chat collegata, lo scollegamento e una notifica di
prova. Oggi la prova parte solo da un comando nella chat: l'API non la espone.

## Decisione

- Endpoint `POST /telegram/test-notification`: il contesto `notifications` legge la chat collegata del tenant e
  invia il testo di prova con le stesse regole di R1.8.1, riusando `SendTestNotificationUseCase` (o estendendone il
  comando con la chat del tenant) senza duplicare il testo; senza chat collegata, errore del contesto (409).
- Frontend `notifications`: codice con il link del bot restituito dall'API, stato della chat, scollegamento con
  conferma, pulsante di prova con esito.

## Alternative scartate

- **Prova solo dalla chat**: nessun cambio di API, ma lo scenario della dashboard non si realizza.

## Conseguenze

- La prova dalla chat e quella dalla dashboard producono lo stesso messaggio.
