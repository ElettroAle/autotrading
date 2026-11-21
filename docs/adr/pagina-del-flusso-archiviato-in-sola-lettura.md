# ADR pagina-del-flusso-archiviato-in-sola-lettura — La pagina di un flusso archiviato si apre in sola lettura

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 690 (Task 697, 698); R6.4.8, R1.1.6
- Collegate: ADR 0116 (dashboard), ADR viste-e-comandi-della-pagina-del-flusso
- Verifica: prova

## Contesto e problema

La pagina del flusso cerca il flusso nell'elenco, che esclude gli archiviati (`dashboard/src/features/flows/components/flow-view.tsx:51-53`):
l'indirizzo di un flusso archiviato mostra «Flusso non trovato.», contro R6.4.8.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): pagina in sola lettura, raggiungibile dall'indirizzo e dai link
  che già la nominano (notifiche, avvisi, classifica); l'elenco dei flussi resta senza archiviati.
- ADR 0116: la dashboard non ha logica che l'API non esponga.

## Decisione

- **API**: la lettura del singolo flusso del tenant restituisce anche un flusso archiviato, con il suo stato; l'elenco dei
  flussi resta invariato. Un flusso di un altro tenant resta non trovato.
- **Dashboard**: la pagina del flusso legge il flusso con la lettura singola invece di cercarlo nell'elenco. Per un
  archiviato mostra lo stato «archiviato», nessuna prossima esecuzione (come per il flusso fermo, narrativa di R6.4.8), nessun comando, e le schede (storico, risultati,
  decisioni) in sola lettura.

## Conseguenze

- I link a un flusso archiviato aprono la sua pagina; nessun comando è possibile su di lui.

## Prove

- Scenari in R6.4.8 (dashboard: la pagina dell'archiviato si apre senza comandi e senza la prossima esecuzione; api: la lettura del flusso
  archiviato restituisce lo stato «archiviato»). Unit test della pagina e della rotta.
