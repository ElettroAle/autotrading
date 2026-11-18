# ADR test-della-dashboard-deterministici — Test della dashboard con lo stesso esito a ogni esecuzione

- Stato: proposta (18 novembre 2026)
- Requisiti: Bug 610, Task 611
- Collegate: `.claude/rules/tech-dashboard.md` §Prove, `.claude/rules/tests.md`
- Verifica: prova

## Contesto e problema

Alcuni test Vitest della dashboard falliscono a caso sotto carico: `back-button.test.tsx` e il primo test di vari file,
che scadono su `findBy` (1 s) o sul timeout del test (5 s). Cause note o probabili: `QueryClient` creati nei test senza
la configurazione della piattaforma (`new QueryClient()` in 6 file, con i tentativi ripetuti e l'attesa esponenziale di
TanStack Query), il costo del primo render di ogni file (trasformazione e import pigri) che ricade sul primo test,
stato condiviso tra test (cronologia del router, fakePlatform, timer).

## Fattori decisionali

- Proprietario (17/11/2026): un test non riproducibile non va bene, va risolto.
- Nessuna prova disattivata, nessun nuovo tentativo dei test, nessuna soglia abbassata.

## Decisione

- Ogni test che usa TanStack Query passa da `src/testing/test-utils.tsx` o crea il client con `queryConfig` della
  piattaforma (senza tentativi ripetuti); nessun `new QueryClient()` nudo nei test, verificato da una regola ESLint
  `no-restricted-syntax` sui file di test.
- Il costo del primo render non ricade sul test: gli import pigri delle rotte si risolvono prima del test (import
  statico nei test o attesa esplicita del modulo in `beforeAll`), non alzando i timeout.
- Ogni causa trovata riproducendo l'errore (stato condiviso, timer reali, cronologia del router in `back-button`) si
  corregge alla radice; il resoconto nomina causa e correzione per ogni test.
- Prova di stabilità: la suite del progetto `browser` passa 10 volte di fila con ordine casuale (`--sequence.shuffle`)
  e con il numero di worker predefinito, quello della pipeline; la configurazione di Vitest non supera i processori
  disponibili. Il comando è uno script `npm run test:stability` documentato in tech-dashboard.md, eseguito dallo
  sviluppatore, non nei job obbligatori. Più worker dei processori misurano una contesa della CPU che né la pipeline né
  lo sviluppo hanno (blocchi del ciclo degli eventi fino a 1,6 s per render sincroni), non un difetto dei test.
- Un timeout più alto è ammesso solo dove la causa è un costo fisso misurato e non riducibile, col motivo in un commento.

## Alternative scartate

- Alzare `asyncUtilTimeout` e `testTimeout` per tutti: nasconde le cause.
- Nuovi tentativi dei test falliti: un test instabile resta instabile.

## Conseguenze

- Un rosso nei controlli della dashboard indica sempre un difetto vero.
