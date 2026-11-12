# ADR 0068 — Riduzione del capitale sulla liquidità del flusso

- Stato: accettata (12 novembre 2026)
- Requisiti: Bug 158 (B1.1.1), R1.1.7, R1.6.1
- Collegate: ADR 0053 (capitale allocato), 0067 (un solo margine); supera in parte ADR 0053 per la regola di
  ammissione della riduzione

## Contesto

L'ADR 0053 ammetteva una riduzione del capitale allocato se il nuovo capitale non scendeva sotto il margine impegnato
dalle posizioni del flusso. Le perdite realizzate e le commissioni restavano fuori: con capitale 400, margine 150 e
PnL realizzato -300, la riduzione a 150 era ammessa e la liquidità del flusso (R1.6.1) diventava
150 - 300 - 150 = -300. Il proprietario ha deciso che una riduzione non porta mai sotto zero la liquidità del flusso.

## Decisione

- **Regola**: una riduzione è ammessa se, con il nuovo capitale, la liquidità disponibile del flusso resta maggiore
  o uguale a zero. La liquidità è quella di R1.6.1: capitale + PnL realizzato dai suoi ordini - loro commissioni -
  margine dichiarato dall'exchange per le sue posizioni (ADR 0067).
- **Una sola fonte**: `ChangeAllocatedCapitalUseCase` legge lo stato con `ReadFlowStateUseCase`, lo stesso dell'API
  `GET /flows/{id}/state`, e lo controlla col nuovo capitale (`require_reduction_within(FlowState)` nel dominio).
- **Capitale minimo del flusso** = margine + commissioni - PnL realizzato, cioè il capitale che porta la liquidità a
  zero. Il rifiuto lo nomina: `CapitalBelowFlowMinimumError` (422), "capitale allocato sotto il minimo del flusso:
  360 USDC". Sostituisce `CapitalBelowCommittedMarginError`.
- Un aumento non legge lo stato del flusso: resta controllato sul capitale libero del conto (ADR 0053).

## Alternative scartate

- **Solo margine** (ADR 0053): lascia togliere al flusso capitale che ha già perso, e il rischio lo dimensiona poi su
  una liquidità negativa.
- **Registro interno del PnL**: è oggetto del Bug 154; la regola qui resta la stessa e prenderà i numeri da lì
  quando lo stato del flusso li leggerà dal registro.

## Conseguenze

- Il testo e gli scenari di R1.1.7 dicono la nuova regola; il messaggio di rifiuto cambia.
- Lo stato del flusso conta il PnL realizzato dalle esecuzioni che l'exchange restituisce ancora (limite delle
  10000 esecuzioni dell'ADR 0044) finché il Bug 154 non è risolto.
