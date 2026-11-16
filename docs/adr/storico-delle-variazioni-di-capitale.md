# ADR storico-delle-variazioni-di-capitale — Storico delle variazioni di capitale del flusso e del conto

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.4.2 (465), Task T3.4.2.1 (489)
- Collegate: ADR 0053 (cronologia del capitale allocato), ADR incasso-dei-profitti, ADR
  tabella-condivisa-senza-sforamento-e-con-filtri, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune, ADR
  filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api, ADR permanenza-decisa-dall-errore-base

## Contesto e problema

La cronologia del capitale allocato esiste già (R1.1.7, `GET /flows/{flow_id}/capital-changes`), dalla più vecchia,
senza motivo né pagine. R3.4.2 vuole motivo, importo, capitale prima e dopo, lo storico del conto con i depositi e i
prelievi dichiarati dall'exchange, pagine dalla più recente e filtro per periodo, nell'API e nella dashboard.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali e componenti riusabili (tabella condivisa, schede
  `ViewTabs`, periodo comune), nessun duplicato per pagina.
- CLAUDE.md: niente ponti; il contesto che usa un dato di un altro sistema dichiara la propria porta, realizzata
  dall'adapter di quella tecnologia.
- ADR 0053: la variazione si registra già con data, importo prima e dopo e utente.

## Opzioni considerate

1. Estendere la cronologia esistente con motivo (`aumento`, `riduzione`, `incasso`) e importo sulla variazione (ADR
   incasso-dei-profitti), e portare `ListCapitalChangesUseCase` a pagine dalla più recente con periodo. Un nuovo
   `ListAccountCapitalChangesUseCase` unisce, in ordine di istante, le variazioni dei flussi del conto e i movimenti
   del conto letti dall'exchange da una porta di `flows`, `AccountTransfersPort` (depositi e prelievi con data,
   importo e verso), realizzata dall'adapter Hyperliquid (`userNonFundingLedgerUpdates`).
2. Salvare in tabella anche depositi e prelievi: scartata, perché l'exchange li dichiara già e si leggono al momento
   come gli altri dati del conto.

## Esito della decisione

Opzione 1.

- API: `GET /flows/{flow_id}/capital-changes` e `GET /accounts/{account_id}/capital-changes`, con `page`, `from` e
  `to`. Ogni riga ha istante, flusso (assente per i movimenti del conto), motivo, importo, capitale prima e dopo
  (assenti per i movimenti). Le variazioni restano sotto RLS come oggi. Un errore dell'exchange nella lettura dei
  movimenti rende l'exchange non disponibile: mai uno storico parziale presentato come completo.
- Dashboard: una scheda «Capitale» nella pagina del flusso (con `ViewTabs` e il periodo comune) e una rotta
  `/accounts/:accountId/capital` raggiunta dalla pagina Conti, entrambe con la tabella e la paginazione condivise.

Verifica: prova (scenari di R3.4.2; test di integrazione dell'adapter sqlalchemy e di quello Hyperliquid sulla
testnet; unit test dei casi d'uso e della tabella).

### Conseguenze

- L'ordine della cronologia esistente passa alla più recente prima: la parte della dashboard che la mostra oggi si
  allinea.
