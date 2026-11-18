# ADR peso-delle-fonti-nel-system-prompt — Regola del peso delle fonti nel segnaposto `{source_weights}` del system prompt

- Stato: proposta (19 novembre 2026)
- Requisiti: Bug 622, Task 623; R1.3.2, R1.4.8; RF-14.02 di `docs/requirements.md`
- Collegate: ADR system-prompt-del-flusso-come-modello-con-segnaposti; `.claude/rules/context-agent.md`,
  `.claude/rules/context-flows.md`
- Verifica: prova

## Contesto e problema

Il peso di ogni fonte (intero da 1 a 10, predefinito 5: `domain/flows/selections.py`) arriva al modello solo come
campo «peso» dei documenti delle fonti nel contesto (`domain/agent/agent_context.py`, `_source_document`).
`DEFAULT_SYSTEM_PROMPT` (`domain/flows/system_prompt.py`) non dice che cosa farne: in dev l'agente ha deciso contando
i segnali, con il forecast a peso 10 pari a un singolo indicatore. RF-14.02 chiede che l'agente tenga conto dei pesi
nel ragionamento.

## Fattori decisionali

- Proprietario (19/11/2026): le istruzioni del flusso prevalgono sui pesi quando li contraddicono, e il prompt lo
  dichiara; la regola sta in un segnaposto dedicato `{source_weights}`, così un system prompt personalizzato la può
  inserire.
- Bug 622: nessun calcolo numerico sui pesi nel codice, nessuna modifica alla configurazione dei flussi esistenti.
- ADR system-prompt-del-flusso-come-modello-con-segnaposti: `PromptPlaceholder` è l'unico registro dei segnaposti;
  testo predefinito, controllo, rendering, API e dashboard ne derivano.
- I limiti del peso hanno una sola definizione (`MINIMUM_WEIGHT`, `MAXIMUM_WEIGHT`, `DEFAULT_WEIGHT`).

## Decisione

- `PromptPlaceholder.SOURCE_WEIGHTS = "source_weights"`, descrizione «la regola del peso delle fonti e i pesi delle
  fonti attive del flusso». Il valore è un testo costruito dal domain con le costanti del peso:
  - il peso è un intero da `MINIMUM_WEIGHT` a `MAXIMUM_WEIGHT` (predefinito `DEFAULT_WEIGHT`), l'importanza relativa
    che l'utente dà a ogni fonte;
  - quando le fonti sono in disaccordo prevale quella col peso più alto, non il numero dei segnali;
  - più valori della stessa fonte (per esempio medie, MACD e RSI degli indicatori) contano come una fonte sola, col
    suo peso;
  - le istruzioni del flusso prevalgono sui pesi quando li contraddicono;
  - nel ragionamento di un'apertura nomina la fonte che ha deciso la direzione quando le fonti erano in disaccordo;
  - i pesi delle fonti attive del flusso, nell'ordine della configurazione (per esempio «forecast 10, indicatori 2»).
- `DEFAULT_SYSTEM_PROMPT` inserisce `{source_weights}` tra le regole operative. Un flusso che segue il predefinito
  riceve la regola senza cambiare configurazione; un system prompt personalizzato salvato prima non cambia (R1.4.8).
- API e dashboard elencano il segnaposto nuovo dal registro, senza codice dedicato.
- Specifiche: R1.3.2 riceve gli scenari del Bug (regola nel predefinito, segnaposto in un prompt personalizzato);
  R1.4.8 elenca `{source_weights}` tra i segnaposti.

## Alternative scartate

- Testo fisso solo nel predefinito: i flussi con un prompt personalizzato non riceverebbero la regola (proprietario).
- Pesi applicati nel codice (punteggi, filtri): escluso dal Bug; la decisione resta del modello.

## Conseguenze

- Il system prompt predefinito si allunga di poche righe; il modello riceve i pesi due volte, nella regola e nel
  contesto, con lo stesso valore.
