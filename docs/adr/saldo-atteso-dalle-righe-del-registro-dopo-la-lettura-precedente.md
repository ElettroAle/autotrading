# ADR saldo-atteso-dalle-righe-del-registro-dopo-la-lettura-precedente — Saldo atteso dalle righe del registro successive alla lettura precedente, chiunque le abbia registrate

- Stato: proposta (20 novembre 2026)
- Requisiti: Bug 633 (Task 634); R1.6.2, R3.3.1
- Precisa: ADR saldo-atteso-con-le-sole-righe-successive-alla-lettura-precedente (il filtro per istante resta; cambia
  l'insieme delle righe a cui si applica)
- Collegate: ADR allarme-di-riconciliazione-sul-saldo-del-conto, ADR 0063 (registro delle operazioni), ADR 0076
  (rilettura di un'ora del registro), ADR inversione-in-due-passi-nel-ciclo, ADR incasso-dei-profitti;
  `.claude/rules/context-flows.md`, `.claude/rules/tech-sqlalchemy.md`
- Verifica: prova

## Contesto e problema

`ReconcileAccountUseCase` spiega il saldo letto con le righe che `RecordAccountExecutionsUseCase` restituisce nella
sua stessa chiamata: solo quelle appena scritte. Il registro però si scrive anche altrove: l'inversione
(`ReverseCyclePositionsUseCase`) registra le esecuzioni della chiusura subito dopo l'ordine, e l'incasso dei profitti
fa lo stesso. Una riga registrata da quei percorsi tra due letture non è più nuova per la riconciliazione e non entra
mai nel saldo atteso.

Il 20 novembre 2026 alle 15:26:33 UTC l'inversione BTC sul conto testnet ha chiuso uno short con PnL realizzato
4,624658 e commissioni 0,064328, registrati alle 15:26:37. La riconciliazione delle 15:27:09 ha atteso 1000,833347
contro 1005,393829 letti: scarto 4,560482, l'esatto netto della chiusura, oltre la soglia. L'allarme resta aperto e
ogni lettura successiva vede lo stesso scarto finché l'utente non conferma.

## Fattori decisionali

- R3.3.1: saldo atteso = riferimento + esecuzioni, commissioni e funding dei flussi + movimenti dichiarati, da allora,
  ognuno contato una volta.
- ADR saldo-atteso-con-le-sole-righe-successive-alla-lettura-precedente: una riga conta se il suo istante è successivo
  alla lettura precedente. L'istante dell'evento, non quello della registrazione, garantisce il conteggio unico.
- ADR 0063: il registro scrive ogni riga una volta, chiunque la registri; resta la fonte delle righe.
- Decisione del proprietario (20 novembre 2026, in chat): contare tutte le righe dei flussi successive alla lettura
  precedente, chiunque le abbia registrate, e aggiungere subito l'indice per la lettura per istante.
- Domain senza I/O: la regola resta in `AccountReconciliation`.

## Decisione

- `FlowLedgerPort` ha un metodo nuovo, `recorded_after`, che restituisce, come `AccountLedger`, le esecuzioni e il funding
  del conto con istante successivo a un momento dato, già registrati (`executed_at > since`, `paid_at > since`).
- `ReconcileAccountUseCase`, dopo aver registrato le righe nuove, legge dal registro quelle successive alla lettura
  precedente e le passa ad `AccountReconciliation.of`, che le usa per `_explained` (solo quelle con flusso, come oggi). Una riga spiega il saldo solo se il suo istante
  è successivo alla lettura precedente e non successivo alla lettura corrente: il registro si legge dopo l'exchange, e
  una riga registrata nel frattempo da un altro flusso dello stesso conto la conta la lettura successiva.
  Senza lettura precedente non le legge.
- Le righe appena registrate restano la base di ciò che è nuovo: esecuzioni sconosciute (R1.6.2), chiusure fuori
  piattaforma e chiusure per protezione. Nessun cambio a registro, totali dei flussi, inversione o incasso.
- Indici per la lettura per istante: `account_fills (tenant_id, account_id, executed_at DESC)` esiste già dalla
  migrazione 0017 e serve anche questa lettura; la migrazione 0052 aggiunge
  `account_funding (tenant_id, account_id, paid_at DESC)`, che serve anche `recorded_since`.

## Alternative scartate

- Far restituire all'inversione e all'incasso le righe registrate, da sommare nella riconciliazione: lega casi d'uso
  indipendenti e dimentica il prossimo percorso che registra.
- Registrare solo nella riconciliazione: l'inversione ha bisogno della chiusura registrata prima dell'apertura
  opposta (ADR inversione-in-due-passi-nel-ciclo).
- Filtrare per istante di registrazione (`recorded_at`): orologio diverso da quello della lettura dell'exchange.

## Conseguenze

- Le chiusure registrate da inversione e incasso entrano nel saldo atteso: niente più allarmi finti dopo un'inversione.
- Una query in più per riconciliazione, su poche righe (l'intervallo tra due letture), servita dagli indici.
- L'allarme aperto il 20 novembre 2026 non si chiude da solo: lo conferma l'utente.
