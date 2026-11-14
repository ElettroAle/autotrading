# ADR 0128 — Posizioni aperte con leva, ingresso e PnL percentuale; posizioni chiuse paginate dall'API

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.4 (Task T2.2.4.1), R2.2.5 (Task T2.2.5.1)
- Collegate: ADR 0116, ADR 0119; R1.6.1 (`GET /flows/{id}/state`), R1.6.2 e R1.7.2 (`GET /flows/{id}/closed-positions`),
  R1.7.3 (paginazione per numero di pagina dei cicli), ADR 0018 (numeri come stringhe), RF-23.03

## Contesto e problema

La tabella delle posizioni aperte mostra asset, direzione, dimensione, leva, prezzo d'ingresso, margine e PnL non
realizzato in valore e in percentuale. Oggi lo stato del flusso porta per posizione solo asset, direzione,
dimensione, margine e PnL: leva e ingresso non arrivano dall'exchange fino all'API, e la percentuale non esiste.
La tabella delle posizioni chiuse mostra 50 posizioni per pagina dalla più recente, ma `GET /flows/{id}/closed-positions`
restituisce l'elenco intero. La dashboard non può rimediare da sé (tech-dashboard.md: nessuna logica di business
che l'API non esponga).

## Decisione

- **Posizione aperta**: il value object della posizione del dominio `flows` (`AccountPosition`) aggiunge leva e
  prezzo d'ingresso, e calcola il PnL percentuale come PnL non realizzato su margine (non disponibile con margine
  zero). L'adapter Hyperliquid legge leva e ingresso dalla posizione dell'exchange; il trasporto verso il worker e
  ritorno li porta; `GET /flows/{id}/state` aggiunge `leverage`, `entry_price` e `unrealized_pnl_percent` (stringhe).
- **Posizioni chiuse**: paginazione per numero di pagina come i cicli (R1.7.3): `GET /flows/{id}/closed-positions?page=N`
  (predefinita 1, pagine di 50 dalla più recente) risponde `{page, has_next, positions}`; il caso d'uso e la porta
  del contesto ricevono la pagina, l'adapter SQL usa limite e offset. Scenari e test di R1.6.2 e R1.7.2 si
  aggiornano alla nuova forma.
- **Frontend** `flow-positions`: tabella delle aperte sullo stato del flusso e tabella delle chiuse con la pagina
  nella query string, entrambe con il componente condiviso `data-table` (tabella su desktop, schede sotto 768
  pixel); importi come li dà l'API, formattati in italiano; PnL verde o rosso.

## Alternative scartate

- **Leva, ingresso e percentuale calcolati nel browser**: nessun cambio di backend, ma logica di business fuori
  dall'API.
- **Paginazione per chiave come le operazioni**: stabile con molte righe, ma le posizioni chiuse di un flusso sono
  poche e la dashboard ha già la paginazione per numero dei cicli.
- **Paginazione nel browser sull'elenco intero**: nessun cambio di API, ma la risposta cresce senza limite.

## Conseguenze

- La forma della risposta delle posizioni chiuse cambia: chi la legge (solo la dashboard e i test) si adegua nella
  stessa PR.
