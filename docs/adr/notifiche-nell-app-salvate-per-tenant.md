# ADR notifiche-nell-app-salvate-per-tenant — Ogni notifica salvata per il tenant, con le sue destinazioni, per il campanello

- Stato: proposta (19 novembre 2026)
- Requisiti: US 380 R6.2.1, Task 381
- Collegate: ADR canali-delle-notifiche-come-insieme, ADR destinazioni-delle-notifiche-nella-dashboard, ADR
  notifica-strutturata-con-icona-titolo-e-valori, ADR avvisi-nel-contesto-delle-notifiche, ADR
  outbox-delle-integrazioni-esterne-con-procrastinate; `.claude/rules/context-notifications.md`
- Verifica: prova

## Contesto e problema

`NotifyUseCase` (`application/notifications/notify.py`) accoda un messaggio per ogni canale scelto e disponibile
(Telegram, email); senza canale non resta nulla. R6.2.1 chiede che ogni notifica compaia anche nella dashboard, anche
se Telegram non è collegato o l'invio fallisce, con numero delle non lette, lettura una per una o tutte, conservazione
di 90 giorni.

## Fattori decisionali

- R6.2.1: ogni notifica nel campanello, indipendente da collegamento e invio di Telegram; 90 giorni; per tenant.
- ADR canali-delle-notifiche-come-insieme: un canale è una consegna verso un sistema esterno scelta per evento. Il
  campanello non consegna fuori dalla piattaforma: è lo storico delle notifiche del tenant, non un canale.
- Pattern esistente: `AlertRepositoryPort.open` dimentica gli avvisi risolti oltre la conservazione, senza job a parte.
- Le destinazioni di una notifica sono già `NotificationTarget` (flusso, operazione, avviso).

## Decisione

Scelta senza regola scritta: il campanello riceve **ogni** notifica che la piattaforma genera per il tenant, anche
quando la scelta dei canali dell'evento è vuota o nessun canale è collegato; la notifica di prova compresa.

- Domain (`notifications`): `InboxNotification` (id `InboxNotificationId`, istante, icona, titolo, testo, destinazioni,
  istante di lettura o nessuno); `INBOX_RETENTION = timedelta(days=90)`.
- Application: porta `NotificationInboxPort` legata al tenant: `add(notification, at)` salva e dimentica quelle più
  vecchie di `INBOX_RETENTION`; `list(cursor)` dalla più recente, a pagine (ADR 0074); `unread_count()`;
  `mark_read(id)` (errore `InboxNotificationNotFoundError`, 404, anche per un'altra del tenant) e `mark_all_read()`.
  `NotifyUseCase` salva nella inbox prima di accodare i messaggi dei canali; un errore della inbox è registrato e non
  ferma né il chiamante né i canali, come un messaggio non accodato. Casi d'uso `ListInboxNotificationsUseCase`,
  `CountUnreadNotificationsUseCase`, `MarkNotificationReadUseCase`, `MarkAllNotificationsReadUseCase`.
- SQLAlchemy: tabella `inbox_notifications` con RLS per tenant, indice su tenant e istante; migrazione dopo l'ultima.
- API: `GET /notifications/inbox` (pagine), `GET /notifications/inbox/summary` (`unread_count`),
  `POST /notifications/inbox/{id}/read`, `POST /notifications/inbox/read`. Ogni notifica porta le destinazioni
  strutturate (tipo, etichetta, flusso, asset, istante di chiusura, avviso), non indirizzi.
- Scenari R6.2.1 della parte API sui casi d'uso con adapter finti; il file `.feature` entra in `specs/`.

## Alternative scartate

- Campanello come terzo canale di `NotificationChannel`: seguirebbe la scelta dei canali, mentre R6.2.1 lo vuole per
  ogni notifica, e non consegna a un sistema esterno.
- Leggere le notifiche dall'outbox: senza Telegram collegato non c'è messaggio, e l'outbox è per le consegne.

## Conseguenze

- Una scrittura in più per notifica; la tabella resta entro 90 giorni senza job dedicati.
