# ADR controllo-giornaliero-delle-scadenze — Controllo giornaliero delle scadenze: notifiche alle soglie, avviso aperto, pausa

- Stato: proposta (19 novembre 2026)
- Requisiti: US 383 R6.2.2, Task 385; dipende da Task 384 e da R6.2.1
- Collegate: ADR scadenza-delle-chiavi-letta-o-indicata, ADR avvisi-nel-contesto-delle-notifiche, ADR
  notifiche-nell-app-salvate-per-tenant, ADR canali-delle-notifiche-per-tipo-di-evento, ADR
  permanenza-decisa-dall-errore-base; `.claude/rules/context-notifications.md`, `.claude/rules/context-flows.md`,
  `.claude/rules/tech-apscheduler.md`
- Verifica: prova

## Contesto e problema

Con la scadenza di ogni chiave (Task 384), R6.2.2 chiede notifiche a 30, 7 e 1 giorno prima e alla scadenza, una sola
volta per soglia, su Telegram e nel campanello, con nome della chiave, data e flussi che la usano; la pausa dei flussi
alla scadenza; il rinnovo che azzera le soglie. Il proprietario (19/11/2026): la chiave in scadenza è anche un avviso
aperto nel centro degli avvisi, «attenzione» da 30 giorni, «critica» alla scadenza, risolto da solo al rinnovo.

## Fattori decisionali

- R6.2.2 e la risposta del proprietario del 19/11/2026.
- Gli avvisi vivono in `notifications` (`AlertRepositoryPort`; `AlertResourceKind.KEY` esiste già).
- Niente ponti: `notifications` dichiara la porta delle chiavi che legge; l'adapter della tecnologia la realizza.
- La permanenza degli errori la decide l'errore base: la pausa per scadenza non passa da un override.

## Decisione

- Porta `ExpiringKeysPort` in `notifications` (per tenant): le chiavi con una data, con tipo (conto o fornitore IA),
  id, nome, data e nomi dei flussi che la usano; la realizza l'adapter SQLAlchemy leggendo conti, chiavi e flussi.
- `CheckKeyExpiriesUseCase` (notifications), una volta al giorno per ogni tenant nel worker (job APScheduler alle 06:00
  UTC) e all'avvio del worker: per ogni chiave calcola nel domain la soglia raggiunta a oggi (30, 7, 1, 0 giorni) e,
  se non è già stata notificata per quella data di scadenza, invia la notifica (evento nuovo `KEY_EXPIRY`, canale
  predefinito Telegram, sempre nel campanello) e la registra (`KeyExpiryNoticeRepositoryPort`, chiave: tipo, id,
  data, soglia). Una data nuova riparte da zero perché la chiave del registro la contiene.
- Testi: «la chiave openrouter scade tra 30 giorni», «… tra 7 giorni», «… scade domani», «la chiave openrouter è
  scaduta», con data e flussi. La notifica porta all'avviso.
- Avvisi: tipi `KEY_EXPIRING` (attenzione) e `KEY_EXPIRED` (critica), risorsa `KEY`, risolti dal controllo quando la
  chiave non è più in scadenza o scaduta (rinnovo, data spostata, chiave tolta); alla scadenza si risolve
  `KEY_EXPIRING` e si apre `KEY_EXPIRED`.
- Pausa: il primo passo del ciclo controlla la scadenza della chiave del conto e del fornitore IA del flusso (porte di
  `flows`); con una chiave scaduta il ciclo non parte e il flusso va in pausa col motivo «chiave openrouter scaduta»
  attraverso la pausa esistente (R1.2.4, notifica del flusso in pausa compresa). Lo stesso fa il controllo giornaliero
  per i flussi attivi.

## Alternative scartate

- Pausa come errore permanente nuovo: richiederebbe un override della permanenza, escluso senza il proprietario.
- Una notifica per ogni ricontrollo: R6.2.2 vuole una sola notifica per soglia.

## Conseguenze

- Un job giornaliero in più nel worker; al più una notifica per soglia e per chiave.
