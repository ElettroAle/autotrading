# ADR resa-della-notifica-per-telegram-ed-email — Resa della notifica per Telegram ed email

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.4 (533), Task T3.5.4.3 (536)
- Collegate: ADR notifica-strutturata-con-icona-titolo-e-valori, ADR canale-email-delle-notifiche-con-smtp, ADR
  outbox-delle-integrazioni-esterne-con-procrastinate, ADR 0035 (collegamento di Telegram e notifiche)

## Contesto e problema

La notifica strutturata deve arrivare a Telegram e all'email con lo stesso contenuto (R3.5.4). Oggi `NotifyUseCase`
accoda per la chat il testo e per l'email oggetto e testo; il bot invia `sendMessage` in testo semplice, senza
`parse_mode`. Serve decidere il formato che viaggia nell'outbox e come lo rendono i due adapter.

## Fattori decisionali

- R3.5.4: l'email ha per oggetto il titolo e lo stesso contenuto del messaggio Telegram.
- `CLAUDE.md`: un adapter = una tecnologia; il contenuto è una regola del domain, non degli adapter.
- `.claude/rules/context-notifications.md`: nessuna credenziale nella notifica. I nomi di flussi e conti sono testo
  dell'utente.
- ADR outbox: il messaggio accodato porta già il testo da consegnare; il worker lo consegna e lo ritenta.

## Opzioni considerate

1. **Testo semplice con emoji, preparato dal domain.** Nell'outbox viaggia `notification.text` (titolo, riga vuota,
   righe dei valori, riga dello stato): per la chat da solo, per l'email insieme a `notification.title` come
   oggetto. Telegram lo invia come oggi, senza `parse_mode`: le emoji sono caratteri Unicode e il testo dell'utente
   (nome del flusso) non ha bisogno di escape. L'email è `text/plain; charset=utf-8` con oggetto codificato in UTF-8
   da `EmailMessage`. Gli adapter non cambiano formato: cambia solo il testo che prepara il domain.
2. HTML di Telegram (`parse_mode=HTML`) con il titolo in grassetto ed escape del testo dell'utente: scartata per ora.
   Aggiunge una regola di escape in due adapter per un solo grassetto, e un escape mancato fa rifiutare il messaggio.
3. Payload strutturato nell'outbox, reso dagli adapter: scartata, il contenuto si deciderebbe in due cartelle.

## Esito della decisione

Opzione 1. I test degli adapter verificano che un testo su più righe con emoji arrivi intatto: a Telegram nel corpo
JSON di `sendMessage`, all'email nel corpo e nell'oggetto. Lo scenario «Stessa notifica per email» verifica che
oggetto e corpo corrispondano al messaggio della chat.

Verifica: prova (test degli adapter Telegram e SMTP con testo su più righe ed emoji; scenario di R3.5.4).

### Conseguenze

- Se in futuro serve il grassetto, una nuova ADR sostituisce questa con l'HTML e la sua regola di escape.
