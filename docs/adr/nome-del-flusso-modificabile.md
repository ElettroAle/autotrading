# ADR nome-del-flusso-modificabile — Il nome del flusso si modifica dall'editor

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 558, Task 559
- Collegate: ADR bozza-configurata-dall-editor-e-duplica-con-conto
- Verifica: prova

## Contesto e problema

Il nome di un flusso si sceglie solo alla creazione: `ModifyFlowCommand` non ha un nome e il form dell'editor lo
mostra in sola lettura (`nameFixed` in `features/flow-editor/components/edit-flow.tsx`). Una copia si chiama
«<nome> (copia)» e non si può rinominare.

## Fattori decisionali

- Bug 558: il nome si modifica nella configurazione e si salva con lei.
- Il nome è unico nel tenant (`FlowNameInUseError`, già usato da creazione e Duplica).
- Il nome non fa parte della strategia: non cambia la versione della configurazione.

## Decisione

- `ModifyFlowCommand.name: str | None`; `ModifyFlowUseCase` lo valida con `FlowName` e rifiuta con
  `FlowNameInUseError` il nome di un altro flusso del tenant; in ogni stato tranne archiviato. Il nome si salva sul
  flusso senza nuova versione della configurazione; una modifica del solo nome non crea versioni.
- API: `name` facoltativo in `FlowModificationRequest`; dashboard: campo Nome modificabile, `nameFixed` sparisce.

## Alternative scartate

- Un comando di rinomina separato: un secondo ingresso dalla stessa pagina di configurazione.

## Conseguenze

- Elenchi, classifica e notifiche mostrano il nome nuovo dal salvataggio in poi.
