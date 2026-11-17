# ADR scenari-del-costo-delle-chiamate-fallite — Gli scenari delle chiamate fallite in R1.4.6

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 541 (Task 544), R1.4.6
- Collegate: ADR uso-riportato-nell-errore-della-chiamata-al-modello, ADR costo-della-decisione-fallita-nel-registro-del-ciclo

## Contesto e problema

Il Bug 541 descrive il comportamento atteso con due scenari. Lo schema dei Bug precedenti (373, 503, 506) mette gli
scenari di un Bug in coda al `.feature` del requisito che correggono, con una frase nella narrativa.

## Fattori decisionali

- `specs.md`: il `.feature` è la fonte del requisito e la board si riallinea al file.
- Testo identico a quello della descrizione del Bug.

## Decisione

- In coda a `specs/E1-flussi-autonomi/F1.4-agente-ia/R1.4.6-costo-delle-chiamate.feature` i due scenari del Bug
  541, «Chiamata pagata senza risposta utilizzabile» e «Chiamata senza risposta dal fornitore», e nella narrativa la
  frase: anche una chiamata che il ciclo non può usare registra l'uso riportato; una chiamata partita di cui nessuno
  conosce il costo conta tra le chiamate senza costo noto (Bug 541).
- La US R1.4.6 sulla board si riallinea al file.

## Alternative scartate

- **Un `.feature` a sé per il Bug**: separerebbe dal requisito le regole sul costo.

## Conseguenze

- Gli scenari si eseguono sui casi d'uso con adapter finti, come gli altri di R1.4.6.
- Verifica: prova (scenari).
