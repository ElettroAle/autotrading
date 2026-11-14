# ADR 0125 — Duplicazione e assegnazione della bozza dalla dashboard

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.4.1 (Task T2.4.1.2)
- Collegate: ADR 0116, ADR 0119, ADR 0124 (flusso in bozza e API)

## Contesto e problema

Dalla dashboard l'utente duplica un flusso e poi, sulla bozza, sceglie conto, capitale e asset prima di avviarla.

## Decisione

- Comando «Duplica» nella pagina del flusso: `POST /flows/{flow_id}/duplicate`, poi navigazione alla bozza creata.
- Sulla bozza, form di assegnazione con React Hook Form + Zod (ADR 0116): conto dall'elenco dei conti, capitale,
  asset; invio a `PUT /flows/{flow_id}/assignment`; gli errori dell'API (Problem Details) accanto ai campi.
- L'avvio usa il comando esistente; la bozza mostra l'etichetta «Bozza» e nessun dato di rendimento.
- Dopo ogni comando si invalidano le query dei flussi.

## Alternative scartate

- **Assegnazione nella stessa finestra della duplicazione**: un passo in meno, ma contraddice la bozza decisa dal
  proprietario (la copia nasce ferma, senza conto).

## Conseguenze

- L'importazione (R2.5.2) riusa lo stesso form di assegnazione.
