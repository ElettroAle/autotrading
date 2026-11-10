# ADR 0016 — Autenticazione OIDC sull'API, chiusa finché la directory non è dichiarata

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.1.1, R0.1.2

## Contesto

R0.1.1 chiede che entri solo chi ha il ruolo applicativo `Utente` nella directory, che chi non lo ha
sia respinto con il motivo "ruolo Utente assente" senza che nasca un tenant, che una richiesta senza
identità sia respinta da qualunque funzione e che la revoca del ruolo tolga l'accesso al token
successivo. L'architettura (§7.1) fissa un IdP OIDC generico, Entra ID come primo, validazione con le
chiavi JWKS dell'issuer e pagina OpenAPI con login Authorization Code + PKCE. La app registration in
Entra non esiste ancora: la farà il proprietario alla fine dell'epica. Il rilascio dev deve
continuare a funzionare nel frattempo.

## Decisione

- **Verifica nel solo adapter FastAPI** (`adapters/inbound/api/authentication.py`) con PyJWT:
  firma RS256 con la chiave dell'issuer scelta per `kid`, `iss` e `aud` attesi, `exp`, `iss`, `aud`
  e `oid` obbligatori. Nessun altro algoritmo è ammesso, quindi un token firmato con un segreto
  condiviso è respinto.
- **Chiavi dall'issuer**: il documento di discovery (`<issuer>/.well-known/openid-configuration`)
  indica `jwks_uri`; le chiavi restano in memoria e si riscaricano solo quando arriva un `kid`
  sconosciuto (rotazione). Solo HTTPS, timeout di 5 secondi. Issuer irraggiungibile: 503
  "directory non raggiungibile".
- **Ruolo**: il claim `roles` deve essere una lista che contiene `Utente`, altrimenti 403
  "ruolo Utente assente". La verifica avviene prima di qualunque caso d'uso, quindi chi non ha il
  ruolo non arriva mai a `ResolveTenantUseCase` e nessun tenant nasce per lui.
- **Identità**: l'utente è l'`oid` del token, mai il nome visualizzato (R0.1.2).
- **Tutte le funzioni dietro un router protetto**: ogni rotta nuova si aggiunge a quel router ed
  eredita la verifica. Restano pubbliche solo `/health`, letta dal controllo di salute del rilascio,
  e le pagine della documentazione OpenAPI.
- **Mappa unica degli errori** in `adapters/inbound/api/errors.py`: 401 "non autenticato" con
  `WWW-Authenticate: Bearer`, 403, 503.
- **`GET /me`** restituisce `user_id` (`oid`) e `tenant_id`, risolto o fondato al primo accesso
  (R0.1.2). È la prima funzione protetta e rende osservabili i due requisiti dalla pagina OpenAPI.
- **Configurazione pubblica**: `AUTH_ISSUER`, `AUTH_AUDIENCE`, `AUTH_CLIENT_ID`, `AUTH_SCOPE` come
  variabili degli environment GitHub, scritte nel `.env` dell'installazione dal rilascio. Non sono
  segreti. Se `AUTH_ISSUER` è vuoto l'installazione parte, ma ogni funzione protetta risponde 503
  "autenticazione non configurata": si fallisce chiusi. Se `AUTH_ISSUER` c'è e manca uno degli
  altri tre valori, l'installazione non parte.
- **API collegata al database** con il ruolo `autotrading_app` e la password come secret montato
  (ADR 0015).

## Alternative scartate

- **Libreria di integrazione Entra (MSAL, fastapi-azure-auth)**: lega l'applicazione a Entra ID,
  mentre l'architettura vuole un OIDC generico sostituibile.
- **Configurazione OIDC obbligatoria all'avvio**: il rilascio dev fallirebbe fino alla
  registrazione in Entra, bloccando le altre consegne dell'epica.
- **Accesso aperto senza issuer in dev**: una funzione raggiungibile senza identità contraddice
  R0.1.1 anche in dev.
- **Chiavi scaricate a ogni richiesta**: una chiamata di rete per richiesta e un IdP lento rallenta
  ogni risposta.

## Conseguenze

- Dopo la registrazione in Entra (passo manuale di fine epica) bastano le quattro variabili
  nell'environment `dev` e un rilascio.
- Un token con un `kid` sconosciuto fa riscaricare le chiavi: un attaccante può causare richieste
  all'issuer, limitate dai suoi tempi di risposta. Se servirà, si aggiungerà un intervallo minimo.
- Le funzioni future si aggiungono al router protetto; il test dello scenario "richiesta senza
  identità" le prova tutte, perché legge le rotte dal documento OpenAPI.
