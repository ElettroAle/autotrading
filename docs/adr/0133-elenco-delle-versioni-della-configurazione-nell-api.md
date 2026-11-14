# ADR 0133 — Elenco delle versioni della configurazione nell'API e confronto affiancato

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.3.5 (Task T2.3.5.1)
- Collegate: R1.1.3 (versioni, `GET /flows/{id}/versions/{version}` e differenze), ADR 0116, ADR 0119

## Contesto e problema

La dashboard elenca le versioni con numero, data e ora; l'API oggi legge una versione alla volta e le differenze
tra due, ma non le elenca. La tabella `flow_versions` ha già `created_at`.

## Decisione

- Caso d'uso `ListFlowVersionsUseCase` del contesto `flows` ed endpoint `GET /flows/{flow_id}/versions`: numero e
  istante di creazione, dalla più recente, dalla porta del repository dei flussi estesa con la lettura dell'elenco.
- Frontend `flow-versions`: elenco, scelta di due versioni, vista affiancata delle due configurazioni lette con
  l'endpoint esistente, campi evidenziati secondo le differenze dell'API (nessun confronto nel browser);
  «Nessuna differenza» quando l'elenco delle differenze è vuoto.

## Alternative scartate

- **Elenco ricavato chiedendo le versioni da 1 al numero corrente**: nessun endpoint, ma N chiamate e nessuna data.

## Conseguenze

- Il confronto resta uno solo, quello dell'API.
