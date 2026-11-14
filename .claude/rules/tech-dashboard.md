---
paths:
  - "dashboard/**"
---

# Dashboard React + TypeScript

Decisioni in ADR 0116 (struttura e controlli), 0117 (container e percorso `/dashboard`), 0118 (accesso Entra), 0121
(grafici).

## Progetto

- `dashboard/` è un progetto a sé (Vite, React, TypeScript `strict`), fuori dall'esagono come `forecaster/`. Parla
  solo con l'API programmatica di `api` (RF-23.11): nessuna logica di business che l'API non esponga.
- Testi dell'interfaccia in italiano, codice in inglese. File e cartelle in kebab-case, componenti in PascalCase.
- Dipendenze fissate a versione esatta nel `package.json`, `package-lock.json` versionato, `npm ci` ovunque.

## Struttura (bulletproof-react)

```text
dashboard/
  src/
    app/                 rotte (routes/), provider, router: compone le funzionalità
    features/<nome>/     api/ components/ hooks/ types/ utils/ di una funzionalità
    components/ config/ hooks/ lib/ stores/ types/ utils/    codice condiviso
    testing/             setup di Vitest, finti MSW dell'API e dell'identity provider (mocks/)
  server/                server statico dell'immagine (Node, solo libreria standard)
  e2e/                   passi degli scenari Gherkin (scenarios/) e supporto (support/)
  architecture/          prova di architettura (ADR 0116)
```

- Dipendenze in una sola direzione: codice condiviso ──> `features` ──> `app`. Nessun import tra funzionalità; il
  codice di produzione non importa `src/testing`; `src` e `server` non si importano a vicenda.
- Nessun barrel file (`index.ts` che riesporta); import assoluti `@/` verso `src`, relativi dentro una funzionalità.
- Le cartelle `utils` e simili sono ammesse solo qui, per scelta del proprietario: la regola «nessuna cartella
  `common`/`utils`/`shared`» resta per il codice Python.
- Le regole di struttura stanno in `eslint.architecture.js` (`import/no-restricted-paths`, `import/no-cycle`,
  `check-file`); `architecture/structure.test.ts` prova ogni regola rossa su un esempio che la viola, silenziosa su
  uno conforme, e la dashboard intera senza violazioni.

## Librerie

React Router, TanStack Query per i dati dell'API, React Hook Form + Zod per i form (Zod anche per validare le
risposte), Tailwind per lo stile, MSAL (`@azure/msal-browser`, `@azure/msal-react`) per l'accesso. Grafici: Recharts,
unica libreria (ADR 0121), importata solo dai grafici condivisi di `src/components/charts`; le funzionalità passano i
dati (`eslint.architecture.js`). Chiamate HTTP con `fetch`, dal client di `src/lib/api-client.ts`.

## Accesso (ADR 0118)

- Authorization code flow con PKCE, client pubblico, solo in `src/lib/auth.tsx`; cache dei token in `sessionStorage`.
- Il token si rinnova dalla cache o col refresh token, senza frame nascosto: se non si può, la sessione è scaduta e
  l'utente torna alla pagina di accesso con la pagina da riaprire (`returnTo`, solo percorsi della dashboard).
- L'autorizzazione resta sull'API: un 403 mostra «Accesso non consentito: manca il ruolo Utente»; nessun dato prima
  che l'API abbia ammesso l'utente (`features/access`).
- Issuer, client id, scope e ambiente arrivano da `config.json`: senza identity provider la dashboard resta chiusa.

## Container (ADR 0117)

- Stadi `dashboard-build` (Node `-dev`) e `dashboard` (Node, utente non root) del `Dockerfile`, fissati per digest;
  l'ultimo stadio resta l'immagine di `api` e `worker`.
- `server/` legge la build una volta all'avvio e serve solo quei file, con fallback a `index.html`, `/dashboard/health`
  e `/dashboard/config.json` generato dalle variabili pubbliche (`APP_ENVIRONMENT`, `AUTH_ISSUER`, `AUTH_CLIENT_ID`,
  `AUTH_SCOPE`); intestazioni di sicurezza con Content Security Policy.
- Nel compose: sola lettura, nessun segreto, porta solo su `127.0.0.1:8080`. Tailscale Serve la espone su `/dashboard`
  del nome dell'installazione (`deploy/configure-serve.sh` a ogni rilascio, `cloud-init.yaml` per le macchine nuove).

## Prove

- Unit test con Vitest + Testing Library accanto al modulo (`<modulo>.test.ts(x)`); l'API e l'identity provider sono i
  finti MSW di `src/testing/mocks`, che tengono lo stato della piattaforma finta (`fakePlatform`). MSAL è quello vero.
- Scenari: i `.feature` di `specs/E2-*` eseguiti da `playwright-bdd` sulla build servita da `server/`, con il browser
  instradato agli stessi finti MSW. Passi in `e2e/scenarios/<epic>/<feature>/<requisito>.steps.ts`, in kebab-case;
  passi condivisi e fixture in `e2e/support/`. Ogni `Allora` e ogni `E` ha la propria asserzione.
- Ogni prova si vede rossa prima di diventare verde. Copertura di righe e rami oltre il 90% (`vitest --coverage`),
  scenari al 100% (`tools/scenario_coverage.py` legge `dashboard/reports/cucumber.json`).

## Controlli

Passi dei job obbligatori esistenti (`.github/actions/dashboard-*`, `node-setup`, `npm-audit`): `stile` ESLint e
Prettier, `tipi` `tsc`, `architettura` `npm run lint:architecture`, `test` Vitest e Playwright, `copertura del codice`
e `copertura degli scenari` dai report della dashboard, `vulnerabilità` `npm audit` e Trivy sull'immagine.
