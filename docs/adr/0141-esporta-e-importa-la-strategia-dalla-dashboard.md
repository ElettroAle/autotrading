# ADR 0141 — Esporta e importa la strategia dalla dashboard

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.5.2 (Task T2.5.2.2)
- Collegate: ADR 0116, ADR 0119, ADR 0125 (form di assegnazione della bozza), ADR 0130 (Problem Details), ADR 0140

## Contesto e problema

Dalla pagina del flusso l'utente scarica il file della strategia; dalla pagina dei flussi carica un file e sceglie
il nome del nuovo flusso, che nasce in bozza.

## Decisione

- «Esporta»: chiamata autenticata a `GET /flows/{flow_id}/strategy`, poi download del contenuto come Blob con il
  nome del file dato dall'API (il link diretto non porterebbe il token).
- «Importa»: form con il nome e il file; il file si legge nel browser come testo e si invia così com'è a
  `POST /flows/import`, senza validarlo nel browser oltre a dimensione e JSON ben formato; gli errori dell'API si
  mostrano col motivo.
- Dopo l'importazione la dashboard apre la bozza con il form di assegnazione di ADR 0125.

## Alternative scartate

- **Upload multipart**: adatto ai file grandi, ma il documento è piccolo e l'API lo riceve come JSON.

## Conseguenze

- Nessuna regola sul formato nel browser: decide l'API.
