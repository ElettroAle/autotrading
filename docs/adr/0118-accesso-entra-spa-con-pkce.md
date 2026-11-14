# ADR 0118 — Accesso alla dashboard con Entra: SPA con PKCE tramite MSAL e token verso l'API

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.1.1 (Task T2.1.1.3)
- Collegate: docs/architecture.md §1 (identità OIDC generica, primo IdP Entra ID), R0.1.1 (accesso solo con il
  ruolo Utente), ADR 0116, ADR 0117

## Contesto e problema

La dashboard deve autenticare l'utente nel browser e chiamare l'API con un token che l'adapter FastAPI già valida
(issuer, audience, ruolo `Utente`). Il browser non può custodire segreti.

## Decisione

- Authorization code flow con PKCE, client pubblico, tramite `@azure/msal-browser` e `@azure/msal-react` nella
  cartella `src/lib` della dashboard. L'app registration è `autotrading-dev` (piattaforma SPA già presente per
  `/docs/oauth2-redirect`), con il redirect URI `https://autotrading-dev.tail8f5e16.ts.net/dashboard/` e
  `http://localhost:5173/dashboard/` per lo sviluppo, aggiunti dall'orchestratore su indicazione del proprietario.
- Il token d'accesso chiesto ha lo scope dell'API già configurato (`AUTH_SCOPE`); il client HTTP della dashboard lo
  aggiunge come `Authorization: Bearer` a ogni chiamata e, su 401, rinnova silenziosamente o riporta al login.
- Cache dei token in `sessionStorage`, non in `localStorage`: chiusa la scheda, serve un nuovo accesso.
- Un utente senza ruolo `Utente` vede la pagina «accesso non consentito» con il 403 dell'API: l'autorizzazione
  resta sull'API, la dashboard non decide nulla.
- L'issuer resta generico (configurazione dell'installazione, ADR 0117): un altro IdP OIDC cambia solo
  la configurazione e la libreria in `src/lib`.

## Alternative scartate

- **Libreria OIDC generica (oidc-client-ts)**: neutra rispetto all'IdP, ma con Entra servono adattamenti che MSAL
  dà già; resta l'alternativa se cambia l'IdP.
- **Backend for frontend con cookie**: nessun token nel browser, ma un nuovo servizio con un segreto, contro la
  scelta del container statico.
- **Implicit flow**: deprecato.

## Conseguenze

- Nessun segreto nella dashboard né nella pipeline per l'accesso.
- Per prod servirà la sua app registration o i suoi redirect URI quando prod verrà attivato.
