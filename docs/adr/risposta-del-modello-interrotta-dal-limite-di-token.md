# ADR risposta-del-modello-interrotta-dal-limite-di-token — Risposta del modello interrotta dal limite di token

- Stato: proposta (24 novembre 2026)
- Requisiti: Bug 733, Task 734; R1.2.3, R1.4.6, R1.4.9
- Collegate: ADR errore-di-openrouter-nella-risposta, ADR uso-riportato-nell-errore-della-chiamata-al-modello, ADR
  tentativi-del-modello-registrati-nel-ciclo, ADR ritentativo-del-modello-nel-ciclo (resta com'è), ADR 0148 (LiteLLM)
- Verifica: prova

## Contesto e problema

Il 23/11/2026 il flusso «Veloce discrezionale» (`openrouter/~deepseek/deepseek-flash-latest`, `max_tokens` 4096,
ragionamento «medio») è fallito alle 13:09 e alle 21:29 con «fornitore IA non raggiungibile: openrouter: risposta del
fornitore inattesa», dopo 4 tentativi. Il registro del ciclo mostra 16384 token di risposta, cioè 4 × 4096. Il modello
ha consumato tutto il limite ragionando e si è fermato prima di scrivere la decisione. OpenRouter ha risposto con
`finish_reason` «length» e senza testo. Anche i cicli conclusi con 2 tentativi hanno questo profilo.

Il fornitore era raggiungibile. Il messaggio porta l'utente a cercare il problema nel posto sbagliato, mentre il
rimedio sta nella configurazione del flusso: alzare `max_tokens` o abbassare il ragionamento.

## Fattori decisionali

- Richiesta del proprietario (24/11/2026): correggere la risposta. Quattro tentativi bastano, non se ne aggiungono.
- R1.2.3: un errore del modello che non dipende dalla chiave o dal credito fa fallire solo il ciclo.
- R1.4.6 e R1.4.9: una chiamata interrotta è addebitata, e il registro ne conta costo e tentativi.
- `CLAUDE.md`: solo OpenRouter può avere codice proprio; per gli altri fornitori vale LiteLLM, senza codice per
  fornitore.

## Decisione

- **Nuovo errore `ModelAnswerTruncatedError`** in `application/agent/errors.py`, sottoclasse di `ModelUnavailableError`:
  ritentativo, costo, tentativi e giornale lo trattano come oggi. Il messaggio è «risposta del modello interrotta dal
  limite di <N> token: alza max_tokens o abbassa il ragionamento del flusso», con N il `max_tokens` della chiamata. Non
  dice «fornitore IA non raggiungibile». `priced` e `with_spend` restituiscono un errore della stessa classe, con lo
  stesso limite.
- Resta temporaneo, come oggi: la permanenza la decide l'errore base, e l'interruzione dipende dalla singola risposta,
  tanto che un nuovo tentativo spesso riesce.
- **Riconoscimento negli adapter**: `OpenRouterModelCallAdapter` e `LiteLlmModelCallAdapter` sollevano
  `ModelAnswerTruncatedError` quando la prima scelta della risposta ha `finish_reason` «length». Questo vale sia senza
  testo sia con un testo parziale, che non è una decisione completa. L'errore porta l'uso riportato e `sent=True`.
- Il numero di tentativi e le attese del modello non cambiano.
- Prova: gli scenari del Bug 733 nel requisito delle chiamate al modello del worker; unit test dei due adapter (risposta
  «length» senza testo e con testo parziale) e dell'errore (`priced` e `with_spend` conservano classe e limite).

## Alternative scartate

- Più tentativi o attese più lunghe: si pagano più chiamate, e la risposta si interrompe di nuovo allo stesso limite.
- Alzare da soli `max_tokens` dopo un'interruzione: cambia il costo del flusso senza che l'utente lo decida.
- Errore permanente che mette in pausa il flusso: un nuovo tentativo spesso riesce, e la pausa fermerebbe un flusso
  che funziona.

## Conseguenze

- Il ciclo fallito e la sua notifica dicono la causa vera e il rimedio.
- Il codice di OpenRouter e quello di LiteLLM leggono entrambi `finish_reason`, che ha lo stesso formato in tutti e due.
