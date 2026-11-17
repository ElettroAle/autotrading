# ADR costo-della-decisione-fallita-nel-registro-del-ciclo — Il ciclo fallito nella decisione registra la chiamata al modello

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 541 (Task 543), R1.4.6, R1.2.3
- Collegate: ADR uso-riportato-nell-errore-della-chiamata-al-modello, ADR 0099, ADR 0104, ADR 0041

## Contesto e problema

Il grafo del ciclo (`application/flows/cycle_graph.py`) mette il costo nello stato solo quando il passo della
decisione ritorna; un ciclo fallito in quel passo si registra con `cost=None`. Il registro dei cicli
(`sqlalchemy/cycle_repository.py`, `costs_within`) legge solo i cicli con `input_tokens` non nullo, così una
chiamata partita senza uso noto non conta neppure tra le «chiamate senza costo noto» delle statistiche.

## Fattori decisionali

- R1.4.6: ogni chiamata registra token e costo; un costo che nessuno conosce si registra come non disponibile e si
  conta a parte, mai come stima (`FlowCost`).
- Fail fast del ciclo (`context-flows.md`): il gestore centrale registra il ciclo fallito; nessun nuovo tentativo.
- Niente ponti tra contesti: `flows` dichiara la sua porta, l'adapter che conosce i tipi dell'agente la realizza.

## Decisione

- `CycleJournalPort` (`application/flows/ports.py`) ha un metodo in più, `failed_call(error)`: dall'errore del
  passo della decisione ricava se la chiamata è partita e, se noto, l'uso con il costo. Lo realizza l'adapter
  `json/cycle_journal.py`, che già legge le risposte dell'agente, importando da application solo `errors.py`.
- Il gestore centrale del grafo, per un errore nel passo `AGENT_DECISION`, chiede `failed_call` e mette nel record
  del ciclo fallito la chiamata: `CallCost` con token e costo quando l'uso è noto, oppure una chiamata senza costo
  noto.
- Il registro dei cicli marca la chiamata al modello con una colonna `model_called` (boolean, non nulla, default
  falso; la migrazione la mette a vero per i cicli che hanno `input_tokens`). La migrazione va dopo l'ultima
  migrazione di main al momento del merge. `costs_within` legge i cicli con `model_called` vero; una chiamata senza
  uso noto arriva a `FlowCost` come costo non disponibile.
- `CycleCost.cost` diventa `CallCost | None`: `None` è una chiamata partita senza uso noto, e `FlowCost.of` la conta
  in `unavailable_calls`.

## Alternative scartate

- **Leggere il costo dall'API di OpenRouter dopo un tempo scaduto**: senza l'id della generazione, che arriva solo
  con la risposta, non è possibile.
- **Stimare i token di una chiamata scaduta**: R1.4.6 vieta di sommare stime ai totali.

## Conseguenze

- Totale, costo per giorno e statistiche del flusso contano anche i cicli falliti nella decisione; le statistiche
  mostrano «N chiamate senza costo noto» per le chiamate perse.
- Verifica: prova. Unit test del grafo (ciclo fallito con uso e senza), dell'adapter json e di `FlowCost`; test di
  integrazione del registro e della migrazione.
