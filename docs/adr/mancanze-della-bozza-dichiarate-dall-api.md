# ADR mancanze-della-bozza-dichiarate-dall-api — L'API dichiara cosa manca alla bozza; Avvia disattivato finché manca

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 560, Task 562; R2.4.1, R1.1.2
- Collegate: ADR bozza-configurata-dall-editor-e-duplica-con-conto, ADR assegnazione-della-bozza-nel-form-di-configurazione
- Verifica: prova

## Contesto e problema

Avvia di una bozza (`features/flows/components/start-flow-button.tsx`) è attivo anche senza conto, capitale o asset:
l'avvio fallisce con `FlowAssignmentMissingError`. La panoramica calcola nel browser cosa manca
(`draft-readiness.tsx`, dai campi nulli), duplicando la regola del dominio (`Flow.missing_assignment`).

## Fattori decisionali

- Bug 560: Avvia disattivato finché manca qualcosa, con l'elenco e il rimando «Configura».
- La dashboard non ha logica di business che l'API non esponga (ADR 0116); nessuna copia della regola.

## Decisione

- API: `FlowResponse.missing: list[str]` con `Flow.missing_assignment` («conto», «capitale allocato», «asset») per una
  bozza, vuoto altrimenti; schema della dashboard rigenerato.
- Dashboard: `StartFlowButton` disattivato quando `missing` non è vuoto, con accanto «Per avviarla manca: …» e il
  collegamento «Configura» all'editor del flusso; `draft-readiness.tsx` legge `missing` invece di calcolarlo.
- Prove: unit test dell'API (bozza parziale, completa, flusso avviato) e dei componenti (pulsante disattivato e
  attivo, testo dell'elenco).

## Alternative scartate

- Calcolo nel browser: duplica la regola del dominio.

## Conseguenze

- Un requisito nuovo per l'avvio compare nella dashboard senza cambiarla.
