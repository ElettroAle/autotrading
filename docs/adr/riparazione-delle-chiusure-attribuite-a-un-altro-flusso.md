# ADR riparazione-delle-chiusure-attribuite-a-un-altro-flusso — Migrazione che riporta le chiusure dei flussi al flusso chiuso

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 684; R1.6.3, R1.7.2
- Collegate: ADR chiusure-dei-flussi-con-il-flusso-nell-ordine, ADR 0063 (registro e totali dei flussi), ADR 0064
- Verifica: prova

## Contesto e problema

Prima dell'ADR chiusure-dei-flussi-con-il-flusso-nell-ordine, gli ordini di chiusura di stop, incasso ed emergenza sono
stati registrati senza flusso, e le loro esecuzioni sono andate al flusso che aveva l'asset al momento della
riconciliazione. Su dev tre esecuzioni BTC (21/11/2026 13:41:53 UTC) sono attribuite al flusso
`e86dd38b-5540-4084-bdf5-85735e2a4222` invece che a `6b1c6c48-3d38-4e66-8a27-175e074c49a2`: i totali di entrambi sono
sbagliati e il primo va in pausa a ogni ciclo. I dati si sanano per una via prevista, non a mano.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): migrazione Alembic di riparazione, generica; su prod non trova
  nulla.
- La migrazione gira con il ruolo delle migrazioni, che può aggiornare `orders`, `account_fills`, `flow_totals` e
  `flow_position_totals` (il ruolo dell'applicazione su `account_fills` ha solo `SELECT` e `INSERT`).
- Nessun id di flusso o di riga scritto nella migrazione: la regola deve riconoscere il caso dai dati.

## Decisione

Una migrazione Alembic di dati, nella stessa PR, in una transazione:

1. **Riconosce gli ordini di chiusura di un flusso**: ordini con origine «comando manuale», `flow_id` nullo,
   `reduce_only` vero, e una posizione chiusa in `closed_positions` dello stesso tenant con stesso asset (`coin`),
   motivo di stop, incasso o emergenza e `closed_at` uguale all'`executed_at` dell'ordine. Il flusso è quello della
   posizione chiusa; un ordine che corrisponde a più posizioni chiuse resta com'è.
2. **Valorizza `orders.flow_id`** di quegli ordini.
3. **Riattribuisce le esecuzioni** di `account_fills` di quegli ordini (`order_id`) al flusso dell'ordine, se oggi sono di
   un altro flusso o di nessuno.
4. **Ricalcola** `flow_totals` e `flow_position_totals` dei flussi toccati (vecchio e nuovo) dalle righe di
   `account_fills` e del funding, con la stessa somma che il registro fa riga per riga (ADR 0063).

`downgrade` non ripristina l'attribuzione sbagliata: è vuoto, con un commento che lo motiva.

## Alternative scartate

- Comando dell'API per riattribuire un'esecuzione: più generale, richiede design e interfaccia; scartata dal proprietario.
- Correzione a mano su dev: esclusa (dati sanati solo per una via prevista).
- Migrazione con gli id di dev scritti dentro: non generica, e su prod sarebbe codice morto.

## Conseguenze

- Su dev, dopo il rilascio, il registro di «BTC #1» torna a BTC 0, quello del flusso `e86dd38b-…` perde il +0,00298 e i
  cicli non vanno più in pausa per la differenza; il proprietario riprende il flusso.
- Su prod la migrazione non trova righe.

## Prove

- Test di integrazione della migrazione contro PostgreSQL (marker `integration`, gira nella pipeline): i dati del caso
  di dev ricostruiti (stop, chiusura senza flusso, asset passato a un altro flusso, esecuzioni attribuite a quello)
  vengono riportati al flusso fermato con i totali ricalcolati; un ordine manuale dalla dashboard senza posizione
  chiusa di stop resta senza flusso; una seconda esecuzione della migrazione non cambia nulla.
