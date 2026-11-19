# ADR pannello-del-system-prompt-chiuso — Pannello del system prompt chiuso per impostazione predefinita nel form del flusso

- Stato: accettata (19 novembre 2026, design approvato dal proprietario)
- Requisiti: Bug 624, Task 625; R1.4.8
- Collegate: ADR system-prompt-del-flusso-come-modello-con-segnaposti, ADR peso-delle-fonti-nel-system-prompt;
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

`SystemPromptField` (`dashboard/src/features/flow-editor/components/system-prompt-field.tsx`) mostra sempre il testo
del system prompt (12 righe) e i segnaposti in mezzo al form del flusso, tra Istruzioni e Rischio. Il campo si cambia
di rado e allunga il form.

## Fattori decisionali

- Proprietario (19/11/2026): pannello chiuso per impostazione predefinita, lo si apre per modificarlo.
- Regole della dashboard: componenti condivisi e forme già in uso dove possibile; nessuna logica di business.
- Un errore di validazione non deve restare nascosto in un pannello chiuso.

## Decisione

- Il campo sta in un `<details>` nativo chiuso, con la stessa forma della sezione del ciclo
  (`features/cycles/components/cycle-section.tsx`): `<summary>` «System prompt» con l'etichetta «predefinito» o
  «personalizzato» secondo `system_prompt_default`.
- Aperto, il contenuto non cambia: testo, «Ripristina predefinito», elenco dei segnaposti.
- Il pannello si apre da sé quando il form ha un errore su `system_prompt` (per esempio un segnaposto sconosciuto).
- Vale per la creazione e per la modifica del flusso; il confronto delle versioni non cambia.

## Alternative scartate

- Aperto quando il testo è personalizzato: il proprietario ha scelto chiuso sempre.
- Un pulsante «Modifica» con stato React: `<details>` è già la forma in uso e accessibile senza codice.

## Conseguenze

- Il form del flusso è più corto; chi vuole il system prompt apre il pannello.
