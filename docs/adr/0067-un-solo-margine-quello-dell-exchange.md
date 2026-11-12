# ADR 0067 — Un solo margine: quello dichiarato dall'exchange

- Stato: accettata (12 novembre 2026)
- Requisiti: Bug 157 (B1.6.4), R1.6.1, R1.1.3, R1.1.7
- Collegate: ADR 0044 (stato del flusso dall'exchange), 0047 (storico delle posizioni chiuse), 0053 (capitale
  allocato), 0062 (stato attribuito nel ciclo)

## Contesto

Il margine di una posizione si calcolava in tre modi diversi:

- `FlowState` (R1.6.1) usava il margine che l'exchange dichiara per la posizione (`marginUsed`);
- la riduzione del capitale (R1.1.7) e il divieto di togliere un asset con posizione aperta (R1.1.3) usavano
  dimensione × prezzo di ingresso / leva, letto dallo stato del conto (`FlowPositionsPort.committed_margin`);
- lo storico delle posizioni chiuse (R1.7.2) usa dimensione × prezzo medio dell'esecuzione di apertura / leva.

Con margine incrociato l'exchange calcola il margine sul prezzo di riferimento corrente, non su quello di ingresso:
0,01 BTC entrati a 60000 con leva 10 valgono 60 a ingresso e circa 70 con il prezzo a 70000. Due controlli dello
stesso flusso potevano quindi vedere due margini diversi.

## Decisione

- **Un solo margine nei controlli e nelle viste**: quello dichiarato dall'exchange per ogni posizione
  (`AccountPosition.margin`, da `assetPositions[].position.marginUsed`), letto con `AccountActivityPort`. Lo usano
  lo stato del flusso, la riduzione del capitale (attraverso lo stato del flusso, ADR 0068) e il ciclo (ADR 0062).
- **Posizione aperta su un asset** (R1.1.3): si decide dalle posizioni che la stessa lettura mostra, non da un
  margine maggiore di zero.
- `FlowPositionsPort.committed_margin` sparisce; il bridge `FlowPositionsFromOrders` resta solo per la chiusura.
- **Storico delle posizioni chiuse**: tiene il margine dell'esecuzione di apertura, perché dopo la chiusura
  l'exchange non dichiara più alcun margine per quella posizione. È il margine impegnato al momento dell'apertura,
  base della percentuale di PnL sul margine (ADR 0047).

## Alternative scartate

- **Prezzo di ingresso / leva ovunque**: è un calcolo della piattaforma che diverge da ciò che l'exchange trattiene
  davvero come garanzia, e quindi da ciò che il conto ha libero.
- **Margine del conto intero** (`crossMarginSummary.totalMarginUsed`): non distingue le posizioni dei flussi.

## Conseguenze

- Una riduzione del capitale o la rimozione di un asset leggono il conto dal `worker` come lo stato del flusso; se
  l'exchange non risponde il comando è rifiutato (503) come prima.
- Nello storico il margine resta quello dell'apertura: con margine incrociato può differire dal margine che lo
  stato mostrava poco prima della chiusura.
