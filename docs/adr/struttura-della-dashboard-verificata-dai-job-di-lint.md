# ADR struttura-della-dashboard-verificata-dai-job-di-lint — La struttura dell'intera dashboard la verificano i job di lint

- Stato: accettata (15 novembre 2026), decisione del proprietario
- Requisiti: Bug 397 (Task 398), Bug 394
- Collegate: ADR 0116 e ADR 0121 (ne precisa i controlli: le regole e il loro intento restano), rule `tech-dashboard.md`
  (ne sostituisce la frase sul test della dashboard intera)

## Contesto e problema

`dashboard/architecture/structure.test.ts` aveva, oltre agli esempi per regola, il test `is respected by the dashboard`:
analizzava tutta la dashboard con `eslint.architecture.js`. È lo stesso controllo che fanno già `npm run lint:architecture`
(job `quality / architettura`) e `npm run lint` (`eslint.config.js` include `...architecture`, job `quality / stile`),
entrambi obbligatori sul ramo `main`. Il suo tempo cresce con la dashboard e dipende dalla macchina della CI: con il timeout
predefinito di Vitest scadeva (Bug 394); alzarlo nascondeva soltanto un test instabile per costruzione.

## Fattori decisionali

- Nessuna regola allentata: ogni violazione della struttura resta un controllo obbligatorio rosso.
- Nessun test il cui esito dipenda dalla velocità della macchina.
- Un controllo una volta sola.

## Opzioni considerate

### 1. Togliere il test della dashboard intera; restano gli esempi per regola e i job di lint

- Buona: un solo controllo della dashboard intera, nei job che esistono per questo; gli unit test provano solo le regole.

### 2. Tenere il test con un timeout alto (Bug 394)

- Cattiva: duplica i job di lint e resta legato alla velocità della macchina.

### 3. Togliere `lint:architecture` e tenere il test

- Cattiva: un job obbligatorio diventerebbe un unit test con un timeout; `npm run lint` farebbe comunque lo stesso lavoro.

## Esito della decisione

Opzione 1, decisa dal proprietario. `structure.test.ts` prova ogni regola rossa su un esempio che la viola e silenziosa su
uno conforme; la dashboard intera senza violazioni la verificano `npm run lint:architecture` e `npm run lint`.

### Conseguenze

- `quality / test` non dipende più dal tempo di un'analisi di tutta la dashboard.
- Una violazione piantata in `src` fa fallire `quality / architettura` e `quality / stile` (provato in Bug 397).
- La rule `tech-dashboard.md` dice dove sta ciascuna verifica.
