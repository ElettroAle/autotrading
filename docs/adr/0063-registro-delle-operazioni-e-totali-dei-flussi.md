# ADR 0063 — Registro delle operazioni e totali correnti dei flussi

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.1, R1.6.2, RF-02.02, RF-02.04, RF-13.01; Bug 154
- Collegate: sostituisce ADR 0044 (stato del flusso dall'exchange); ADR 0045 (riconciliazione), ADR 0062 (stato
  attribuito nel ciclo), ADR 0067 (un solo margine)

## Contesto

L'ADR 0044 ricalcolava PnL realizzato e commissioni di un flusso a ogni lettura, sommando le esecuzioni che
Hyperliquid restituisce con `userFillsByTime`. L'exchange conserva solo le 10000 esecuzioni più recenti di un conto:
oltre quella soglia le più vecchie spariscono e i soldi del flusso diventano sbagliati senza alcun segnale. Inoltre
ogni lettura riportava l'intera storia del conto, dall'API e dal ciclo, sempre più lunga.

I requisiti vogliono più flussi sullo stesso conto, ognuno col proprio capitale (RF-02.02, RF-02.04), e una
contabilità virtuale per flusso (RF-13.01). Il proprietario ha scelto di conservare lo storico completo di ogni
esecuzione e di ogni pagamento di funding, leggendo dall'exchange solo ciò che è nuovo, e di tenere totali correnti
che il ciclo legge senza mai sommare lo storico.

## Decisione

- **Domain** (`flows/ledger.py`): `Execution` (fill e ordine dell'exchange, `cloid` se c'è, asset, quantità con
  segno, prezzo, commissione, PnL realizzato, posizione di partenza, liquidazione, istante), `FundingPayment`,
  `ExecutionsWindow` (ciò che l'exchange conserva da un istante, con `complete`), `FlowTotals` (PnL realizzato,
  commissioni, funding, posizione attesa per asset) e `AccountLedger.attributed`, che assegna ogni riga nuova in
  ordine di tempo:
  - ordine della piattaforma: il suo flusso; senza flusso (comando manuale, stop) il flusso che ha l'asset;
  - senza ordine della piattaforma, sull'asset di un flusso: la liquidazione è del flusso (`liquidazione`); la
    chiusura esatta della posizione attesa (posizione di partenza uguale all'attesa, risultato zero) è del flusso
    (`chiusura_fuori`); ogni altra esecuzione non è di nessun flusso (`non_attribuita`);
  - funding: del flusso che ha l'asset con posizione attesa diversa da zero quando è pagato.
- **Caso d'uso** `RecordAccountExecutionsUseCase`, unico punto di scrittura, eseguito dalla riconciliazione del
  conto prima del resto (ADR 0045), all'inizio e alla fine di ogni ciclo: legge il cursore del conto, chiede
  all'exchange le esecuzioni e il funding da cursore meno un minuto, scarta le chiavi già registrate, chiede agli
  ordini della piattaforma solo i `cloid` che le righe nuove nominano, attribuisce e registra.
- **Finestra incompleta**: dal cursore l'exchange restituisce 10000 esecuzioni o più, quindi alcune possono essere
  già sparite. `FlowLedgerIncompleteError` (permanente) ferma il ciclo; `FlowPauseFromFlows` mette in pausa tutti i
  flussi attivi del conto con il motivo "registro delle esecuzioni incompleto" e la notifica (R1.2.4). Alla prima
  lettura, senza cursore, ciò che l'exchange conserva è il punto di partenza.
- **Porte**: `AccountExecutionsPort.since(account_id, since)` (worker, `AccountExecutionsFromAccounts` apre il conto
  solo per l'indirizzo); `FlowLedgerPort` con `cursor`, `recorded_since`, `record`, `totals_of`;
  `PlatformOrdersPort.orders_among(account_id, order_ids)` legge solo gli ordini nominati.
- **Exchange**: `HyperliquidAccountExecutionsAdapter` legge `userFillsByTime` (pagine da 2000) e
  `userFunding` (pagine da 500) dall'istante dato. `HyperliquidAccountActivityAdapter` non legge più le esecuzioni;
  l'attività del conto (posizioni, margine, PnL non realizzato, movimenti) resta quella dell'ADR 0044.
- **Database** (migrazione 0017, RLS per tenant come le altre tabelle):
  - `account_fills` (unica per tenant, conto, fill e ordine dell'exchange; `flow_id` e `order_id` nullable; tipo)
    e `account_funding` (unica per tenant, conto, asset e istante): storico, solo `SELECT` e `INSERT` per il ruolo
    dell'applicazione;
  - `account_fill_cursors`, `flow_totals`, `flow_position_totals`: stato, `SELECT`, `INSERT`, `UPDATE`;
  - indici `(tenant_id, flow_id, executed_at DESC)` e `(tenant_id, account_id, executed_at DESC)` per la lettura
    dello storico a pagine.
  `SqlAlchemyFlowLedgerAdapter.record` inserisce con `ON CONFLICT DO NOTHING ... RETURNING` e aggiorna i totali solo
  per le righe davvero aggiunte, nella stessa transazione; il cursore si sposta con `GREATEST`, mai indietro. Due
  cicli dello stesso conto non contano mai due volte la stessa esecuzione.
- **Stato del flusso**: `FlowState.attributed(flow, activity, totals)`; liquidità disponibile = capitale allocato
  + PnL realizzato − commissioni + funding − margine delle posizioni. Dall'exchange restano solo posizioni, margine,
  PnL non realizzato e margine libero del conto.
- **Verifica**: `recomputed_totals(flow_id)` risomma lo storico in SQL; si esegue su richiesta o dai test, mai nel
  ciclo.
- **Riconciliazione** (ADR 0045): le esecuzioni non spiegate sono le righe nuove che non vengono da un ordine della
  piattaforma; una chiusura fuori è soppressa se una riga nuova sull'asset viene da un ordine della piattaforma.

## Alternative scartate

- **Ricalcolo dall'exchange a ogni lettura** (ADR 0044): perde le esecuzioni oltre le 10000 più recenti.
- **Solo i totali, senza storico**: un totale sbagliato non si potrebbe ricostruire né mostrare all'utente.
- **Somma dello storico a ogni ciclo**: costo che cresce con la vita del flusso; i totali correnti costano una riga.
- **Ordini registrati come fonte delle esecuzioni**: un'esecuzione fuori dalla piattaforma (liquidazione, chiusura
  manuale sull'exchange) non comparirebbe.
- **Pausa del solo flusso del ciclo su finestra incompleta**: il registro è del conto, e tutti i flussi del conto ne
  leggono i totali.

## Conseguenze

- I soldi del flusso restano corretti qualunque sia la vita del conto; l'unico caso non recuperabile, più di 10000
  esecuzioni tra due cicli, ferma i flussi del conto invece di sbagliare in silenzio.
- Un ordine della procedura di verifica (senza flusso) su un asset di un flusso è attribuito a quel flusso, come un
  comando manuale.
- I movimenti del saldo (`userNonFundingLedgerUpdates`) si leggono ancora per intero a ogni lettura dell'attività.
- La lettura dello storico da parte dell'utente (API delle operazioni) e il blocco su posizione diversa da quella
  attesa (Bug 155) si appoggiano su questo registro.
