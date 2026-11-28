# ADR intervallo-di-riconciliazione-del-conto — Intervallo di riconciliazione impostato sul conto

- Stato: accettata (28 novembre 2026, decisione del proprietario)
- Requisiti: Bug 778 (Task 780)
- Collegate: ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte, ADR esposizione-massima-per-direzione-del-conto
  (impostazione del conto con la stessa forma), ADR informazioni-sui-campi-di-configurazione;
  `.claude/rules/context-accounts.md`, `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-fastapi.md`,
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

La riconciliazione periodica legge un conto con posizioni aperte ogni intervallo. Il proprietario vuole questo
intervallo configurabile sul conto, predefinito 5 minuti.

## Fattori decisionali

- Decisione del proprietario (28 novembre 2026): predefinito 5 minuti, configurabile sul conto.
- Le impostazioni del conto seguono la forma dell'esposizione massima per direzione: colonna facoltativa, endpoint
  dedicato, campo nella pagina del conto.
- Ogni campo della dashboard ha il suo pulsante info (ADR informazioni-sui-campi-di-configurazione).

## Decisione

- **Domain** (`domain/accounts`): value object `ReconciliationInterval`, minuti interi da 1 a 1440, con il predefinito di
  5 minuti come costante del value object. Fuori intervallo solleva un errore di dominio con il motivo «intervallo di
  riconciliazione da 1 a 1440 minuti».
- **Persistenza.** Una migrazione aggiunge la colonna facoltativa `reconciliation_interval_minutes` alla tabella dei
  conti. Vuota vale il predefinito. Nessuna migrazione dei dati: i conti esistenti valgono 5 minuti.
- **API.** `PUT /accounts/{id}/reconciliation-interval` con `{"minutes": <intero>}` imposta l'intervallo. La lettura del
  conto riporta `reconciliation_interval_minutes` sempre valorizzato, predefinito compreso.
- **Contesto flows.** La riconciliazione periodica legge l'intervallo del conto attraverso una porta propria di
  `flows`, realizzata dall'adapter SQLAlchemy (niente ponti, ADR 0089).
- **Dashboard.** Nella pagina del conto, campo «Intervallo di riconciliazione (minuti)» con il suo pulsante info e il
  testo: che cosa fa, da 1 a 1440, predefinito 5.

## Alternative scartate

- **Intervallo per flusso**: la riconciliazione legge il conto intero, non il singolo flusso.
- **Intervallo della piattaforma**: il proprietario lo vuole sul conto.

## Conseguenze

- Ogni conto si riconcilia ogni 5 minuti mentre ha posizioni aperte, salvo un intervallo diverso impostato.
