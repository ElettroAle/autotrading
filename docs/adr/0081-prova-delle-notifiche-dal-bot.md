# ADR 0081 — Prova delle notifiche dal bot

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.8.1
- Collegate: ADR 0035 (collegamento di Telegram e notifiche), di cui estende la lettura prima del tenant

## Contesto

Il comando `/prova` inviato al bot dalla chat collegata deve far arrivare una notifica di prova per la stessa strada
delle notifiche dei flussi, così l'utente vede che la consegna funziona. Il messaggio arriva al bot con il solo id
della chat: il tenant non è ancora noto e le tabelle sono protette da row level security per tenant.

L'ADR 0035 risolve lo stesso problema per il codice di collegamento: la transazione dichiara il digest del codice
e una policy di sola lettura mostra solo la riga di quel digest. Una chat può essere collegata a più tenant
(ognuno ha al massimo una chat, ma più utenti possono collegare lo stesso gruppo).

## Decisione

- Una porta di application, `LinkedChatLookupPort.tenants_of(chat_id)`, restituisce i tenant a cui la chat è
  collegata; è l'unica lettura dalle chat prima che il tenant sia noto.
- L'adapter SQL dichiara la chat nella transazione (`app.telegram_chat_id`) e la policy `telegram_chats_by_chat`,
  solo `SELECT`, mostra solo i collegamenti di quella chat.
- Per ogni tenant trovato il caso d'uso invia `Notification.test()` con il `NotifyUseCase` legato a quel tenant,
  lo stesso delle notifiche dei flussi: la prova attraversa repository, formattazione e invio veri.
- Una chat non collegata riceve le istruzioni per il collegamento.
- Il riconoscimento del comando (`/prova`, anche con `@nome_bot` come Telegram lo invia nei gruppi) è una regola
  del dominio; Telegram resta negli adapter.

Dichiarare una chat equivale a esserla: solo Telegram consegna al bot un messaggio di una chat, e il bot è
l'unico a leggere con questa policy.

## Alternative scartate

- **Rispondere direttamente con il messenger**: prova solo che il bot risponde, non che la notifica di un tenant
  raggiunge la sua chat collegata.
- **Leggere le chat senza row level security** (ruolo dedicato o `BYPASSRLS`): apre al bot tutte le chat di tutti
  i tenant per una lettura che ne riguarda una.

## Conseguenze

- Una chat collegata a più tenant riceve una notifica di prova per ciascuno.
- Un invio di prova che fallisce si registra come ogni notifica e non fa fallire il giro del bot.
