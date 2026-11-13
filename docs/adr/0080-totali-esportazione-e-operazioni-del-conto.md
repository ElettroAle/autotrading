# ADR 0080 — Totali, esportazione CSV e tutte le operazioni del conto

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.6.3
- Collegate: ADR 0074 (consultazione del registro delle operazioni), ADR 0063 (registro delle operazioni),
  ADR 0018 (importi nell'API come stringhe con il punto decimale), ADR 0027 (Problem Details)

## Contesto

L'ADR 0074 rende leggibile il registro a pagine di 50 righe, dalla più recente: le operazioni di un flusso e quelle
del conto che non sono di nessun flusso. Il proprietario ha approvato tre criteri in più (R1.6.3):

- i totali del periodo consultato: numero di operazioni, PnL realizzato, commissioni e funding;
- l'esportazione CSV di tutte le righe del filtro, dalla più vecchia;
- tutte le operazioni di un conto insieme, dei suoi flussi e di nessun flusso, ciascuna con il suo flusso.

Il registro cresce per tutta la vita del conto (decine di migliaia di righe): i totali non si possono calcolare
sommando le righe in un ciclo e l'esportazione non può caricarle tutte in memoria.

## Decisione

- **Domain** (`flows/operations.py`): `Operation.flow` (nome del flusso, `None` se di nessun flusso);
  `OperationsQuery.unpaged()` (gli stessi filtri senza il cursore della pagina); `OperationsTotals`,
  `OperationsReport` (pagina e totali); il proprietario delle righe `OperationsOwner`, che è `FlowOperations`
  (un flusso) oppure `AccountOperations` (un conto con un `AccountScope`: `unattributed`, solo le righe di nessun
  flusso, oppure `all`, tutte).
- **Porta** `FlowOperationsPort` con due metodi, al posto di `of_flow` e `unattributed_of_account`:
  - `report(owner, query)`: la pagina e i totali di tutte le righe ammesse dal filtro, qualunque sia la pagina;
  - `export(owner, query)`: tutte le righe ammesse dal filtro, dalla più vecchia, lette mentre si consumano.
  Per un conto che il tenant non ha, entrambi sollevano `FlowAccountNotFoundError`; l'esportazione lo solleva prima
  di restituire, mai mentre le righe vengono lette, perché a quel punto la risposta è già partita.
- **Casi d'uso**: `ListFlowOperationsUseCase` e `ListAccountOperationsUseCase` restituiscono `OperationsReport`; il
  comando del conto porta lo scope. `ExportFlowOperationsUseCase` (verifica il flusso nel tenant prima delle righe) ed
  `ExportAccountOperationsUseCase`.
- **Database** (`SqlAlchemyFlowOperationsAdapter`):
  - le righe sono lo stesso `UNION ALL` dell'ADR 0074 con il `flow_id`, e il nome si prende con un `LEFT JOIN` su
    `flows`, sotto RLS;
  - i totali sono **una sola query aggregata** (`count`, `sum` con `coalesce` a zero) sugli stessi filtri senza
    cursore, nella stessa transazione della pagina: pagina e totali vedono lo stesso stato;
  - l'esportazione legge con un cursore lato server (`yield_per`, 500 righe alla volta) dentro una transazione con
    il tenant impostato: la memoria resta costante qualunque sia la lunghezza del registro;
  - gli indici della migrazione 0017 su (tenant, flusso, istante) e (tenant, conto, istante) servono sia la pagina sia
    l'aggregato; nessuna migrazione nuova.
- **API**:
  - `GET /flows/{flow_id}/operations` e `GET /accounts/{account_id}/operations` aggiungono `totals` (`count`,
    `realized_pnl`, `fees`, `funding`) e su ogni riga `flow` (il nome, `null` per nessun flusso);
  - `GET /accounts/{account_id}/operations` accetta `scope=unattributed|all`; senza `scope` resta `unattributed`, il
    comportamento dell'ADR 0074;
  - `GET /flows/{flow_id}/operations.csv` e `GET /accounts/{account_id}/operations.csv` (con `scope`) rispondono
    `text/csv; charset=utf-8` come allegato `operazioni.csv`, in streaming con `StreamingResponse`, con i filtri
    `asset`, `from`, `to`. Colonne: istante (ISO 8601), flusso (`nessun flusso` se di nessuno), asset, tipo, lato,
    quantità, prezzo, commissione, PnL realizzato, funding. Gli importi hanno il punto decimale e nessuno zero finale,
    con la stessa `amount_text` dell'API (ADR 0018); separatore virgola, righe `CRLF` (RFC 4180).
  - Un flusso o un conto di un altro tenant risponde 404 anche all'esportazione, prima di qualsiasi riga.

## Alternative scartate

- **Totali sommati nel codice dalle righe lette**: costo lineare nel registro a ogni consultazione e memoria
  proporzionale alle righe.
- **Totali dai totali correnti dei flussi (ADR 0063)**: valgono per tutta la vita del flusso, non per un periodo o
  un asset, e non esistono per il conto.
- **Esportazione per pagine successive dell'API**: costringe chi esporta a ripetere le richieste e non è un file
  unico.
- **Esportazione caricata in memoria con `.all()`**: con un registro lungo la memoria del processo cresce senza
  limite.
- **Una nuova porta per l'esportazione**: è la stessa lettura del registro con un altro ordine; un'unica porta tiene
  insieme filtri e proprietario.
- **Virgola decimale nel CSV**: l'API usa il punto (ADR 0018); il file deve riportare gli stessi valori dell'API.

## Conseguenze

- I totali costano una query aggregata sugli indici esistenti, come la pagina.
- L'esportazione tiene una connessione del pool finché il client legge il file; un client lento la occupa più a
  lungo. Il pool dell'API resta dimensionato per poche persone.
- Un errore del database a esportazione iniziata interrompe il file: l'intestazione HTTP è già partita e non può più
  diventare un Problem Details.
- La colonna `funding` si aggiunge alle nove approvate: senza di essa le righe di funding non avrebbero importo.
- `Operation.flow` è sempre presente nella risposta; i client che ignorano campi sconosciuti non cambiano.
