# ADR 0134 — Notifica di prova Telegram anche dall'API, per la pagina delle notifiche

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.3.6 (Task T2.3.6.1)
- Collegate: R1.8.1 (collegamento e prova dalla chat, `SendTestNotificationUseCase`), ADR 0026 (contesto
  `notifications`), ADR 0116, ADR 0119; API `/telegram/link-code`, `/telegram/chat`

## Contesto e problema

La pagina delle notifiche mostra codice e link del bot, la chat collegata, lo scollegamento e una notifica di
prova. Oggi la prova parte solo da un comando nella chat: l'API non la espone.

## Decisione

- Endpoint `POST /telegram/test-notification` (204): il nuovo caso d'uso `SendLinkedChatTestNotificationUseCase` del
  contesto `notifications`, legato al tenant, legge la chat collegata e invia lo stesso testo di prova di R1.8.1
  (`Notification.test()`) per la strada delle notifiche vere (`NotifierPort`, worker); senza chat collegata
  `NoLinkedChatToTestError` (409). `SendTestNotificationUseCase` non si riusa: parte dalla chat e cerca il tenant,
  l'opposto di ciò che serve all'API.
- `GET /telegram/chat` restituisce anche `chat_id`, per mostrare quale chat è collegata.
- Frontend `notifications`: codice con il link del bot restituito dall'API, stato della chat, scollegamento con
  conferma, pulsante di prova con esito.

## Alternative scartate

- **Prova solo dalla chat**: nessun cambio di API, ma lo scenario della dashboard non si realizza.

## Conseguenze

- La prova dalla chat e quella dalla dashboard producono lo stesso messaggio.
