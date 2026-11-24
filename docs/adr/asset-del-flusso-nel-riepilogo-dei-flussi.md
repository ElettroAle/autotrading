# ADR asset-del-flusso-nel-riepilogo-dei-flussi — Asset del flusso nel riepilogo dei flussi

- Stato: proposta (23 novembre 2026)
- Requisiti: Bug 731, Task 732; R2.2.2
- Collegate: ADR 0127 (riepilogo dei flussi), ADR 0124 (bozze senza conto, capitale o asset), ADR
  card-condivisa-distinta-dallo-sfondo
- Verifica: prova

## Contesto e problema

La scheda di ogni flusso nella pagina dei flussi (R2.2.2) mostra stato, guadagni, posizioni, capitale, conto, modello,
versione ed esecuzioni, ma non dice su quali asset opera il flusso. Il proprietario l'ha chiesto il 23/11/2026. La
configurazione del flusso ha già gli asset, e `GET /flows` li espone, ma `GET /flows/overview`, che la scheda usa, non li
espone.

## Fattori decisionali

- Richiesta del proprietario: il riepilogo mostra gli asset coinvolti.
- ADR 0116: la dashboard non ha logica che l'API non esponga, quindi il dato arriva dal riepilogo dell'API e non da una
  seconda chiamata a `GET /flows`.
- Scelta presa senza una regola scritta: «asset coinvolti» sono gli asset della versione in vigore del flusso, cioè
  quelli su cui il flusso può operare, non solo quelli con una posizione aperta. Le posizioni aperte hanno già il loro
  conteggio nella scheda.

## Decisione

- `FlowSummary` del contesto `flows`, letto da `FlowSummaryPort`, porta gli asset della versione in vigore nell'ordine
  della configurazione. `FlowOverviewResponse` di `GET /flows/overview` li espone come `assets: list[str]`, vuota per
  una bozza senza asset.
- La scheda della dashboard (`flow-overview-card.tsx`) mostra una riga «Asset» con gli asset separati da « · » (per esempio
  «ETH · SOL · BTC»), o «nessuno» se la lista è vuota. Lo schema zod di `get-flow-overviews.ts` aggiunge il campo, e il
  client generato dall'OpenAPI si riallinea.
- Prova: gli scenari del Bug 731 in R2.2.2 sotto il sistema dashboard (Playwright) e quello dell'API; unit test della
  risposta, dell'adapter di `FlowSummaryPort` e della scheda.

## Alternative scartate

- Mostrare solo gli asset con posizioni aperte: duplica il conteggio delle posizioni e nasconde su che cosa il flusso
  opera quando non ha posizioni.
- Leggere gli asset da `GET /flows` nella dashboard e unirli al riepilogo: è logica di composizione nella dashboard, e
  costa due chiamate.

## Conseguenze

- Il riepilogo dei flussi cresce di un campo; i flussi con molti asset vanno a capo nella riga, senza troncare.
