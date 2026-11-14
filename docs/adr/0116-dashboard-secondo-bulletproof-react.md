# ADR 0116 — La dashboard segue bulletproof-react, con i controlli nella pipeline esistente

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.1.1 (Task T2.1.1.1)
- Collegate: docs/architecture.md §1 (dashboard React + TypeScript, frontend separato che consuma l'API di F1),
  §2 (container `dashboard`); ADR 0001-0013 (pipeline TrunkFlow e controlli obbligatori)

## Contesto e problema

La fase F2 introduce la dashboard React + TypeScript prevista da `docs/architecture.md` §1. Il contratto del
repository (`CLAUDE.md`, `.claude/rules/`) copre solo il codice Python: struttura, nomenclatura, test e controlli
della dashboard non sono scritti, e senza regole ogni lavoro di E2 sceglierebbe da sé. Il proprietario ha indicato
come riferimento [bulletproof-react](https://github.com/alan2207/bulletproof-react) (decisione dell'avvio di E2,
14 novembre 2026).

## Decisione

- **Dove**: cartella `dashboard/` alla radice, progetto a sé (Vite, React, TypeScript `strict`), fuori dall'esagono
  Python, come `forecaster/`. Parla solo con l'API programmatica di `api` (RF-23.11): nessuna logica di business
  che l'API non esponga.
- **Struttura** di bulletproof-react (`docs/project-structure.md`): `src/app` (rotte, provider, router),
  `src/components`, `src/config`, `src/features/<funzionalità>` (`api`, `components`, `hooks`, `types`, `utils`),
  `src/hooks`, `src/lib`, `src/stores`, `src/testing`, `src/types`, `src/utils`. Dipendenze in una sola direzione,
  condiviso ──> `features` ──> `app`; nessun import tra funzionalità; nessun barrel file; import assoluti `@/`.
  Le cartelle `utils` e simili sono ammesse solo dentro `dashboard/`, per scelta del proprietario: la regola
  «nessuna cartella `common`/`utils`/`shared`» resta per il codice Python.
- **Librerie** del riferimento: React Router, TanStack Query per i dati dell'API, React Hook Form + Zod per i form,
  Tailwind per lo stile, MSAL per l'accesso Entra (al posto dell'autenticazione a cookie del riferimento).
  Grafici: una sola libreria, scelta dal primo lavoro che ne ha bisogno e scritta nella rule.
- **Nomi**: file e cartelle in kebab-case (`check-file`), componenti in PascalCase, testi dell'interfaccia in
  italiano, codice in inglese.
- **Prove**: unit test con Vitest + Testing Library + MSW (l'API finta); scenari Gherkin dei `.feature` di E2
  eseguiti con Playwright tramite `playwright-bdd` contro la build servita con l'API finta; ogni prova si vede
  rossa prima di diventare verde; copertura del codice cambiato oltre il 90% e scenari al 100% come per Python.
- **Controlli**: ESLint (con `import/no-restricted-paths` per le direzioni e i confini tra funzionalità, `jsx-a11y`,
  `testing-library`), Prettier, `tsc --noEmit`, Vitest con copertura, Playwright, `npm audit`. Girano come passi
  dei job obbligatori che esistono già (`stile`, `tipi`, `architettura`, `test`, `copertura del codice`,
  `copertura degli scenari`, `vulnerabilità`), così le regole del ramo non cambiano. I due strumenti di copertura
  (`tools/coverage_gate.py`, `tools/scenario_coverage.py`) leggono anche i risultati della dashboard.
- **Contratto**: una sezione «Dashboard» in `CLAUDE.md` e la rule `.claude/rules/tech-dashboard.md` per
  `dashboard/**`, nell'indice.

## Alternative scartate

- **Struttura per tipo** (`components/`, `pages/`, `services/` piatti): più semplice all'inizio, ma mescola le
  funzionalità e non rispecchia i confini dei requisiti; il proprietario ha indicato bulletproof-react.
- **Nuovi job obbligatori dedicati alla dashboard**: separano bene i risultati, ma richiedono di cambiare le regole
  del ramo protetto, che sono del proprietario.
- **Cypress o solo Testing Library per gli scenari**: Playwright è lo strumento del riferimento e `playwright-bdd`
  esegue direttamente i `.feature`, come pytest-bdd per Python.

## Conseguenze

- Ogni lavoro di frontend di E2 parte da questa struttura e da questi controlli.
- La pipeline installa Node nei job interessati: qualche minuto in più per ogni PR.
- La regola Python sulle cartelle `utils` non si applica a `dashboard/`, e la rule lo dice esplicitamente.
