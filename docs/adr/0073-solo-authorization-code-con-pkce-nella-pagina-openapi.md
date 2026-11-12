# ADR 0073 — Solo Authorization Code con PKCE nella pagina OpenAPI

- Stato: accettata (12 novembre 2026)
- Requisiti: R0.1.1; Bug 164

## Contesto

La pagina `/docs` descriveva il login con uno schema `openIdConnect` che punta al documento di discovery
dell'issuer (ADR 0016). La pagina OpenAPI legge da quel documento tutti i flussi che l'issuer supporta, e
Entra ID dichiara anche il flusso implicito: la pagina offriva quindi due login, Authorization Code e
implicito. Il flusso implicito consegna il token nell'URL ed è deprecato (OAuth 2.0 Security Best Current
Practice, OAuth 2.1). Sull'app Entra è disattivato, ma la pagina lo proponeva comunque.

## Decisione

- **Uno schema `oauth2` con il solo flusso `authorizationCode`**, chiamato `OAuth2`. La pagina mantiene
  `usePkceWithAuthorizationCodeGrant`, quindi il login è Authorization Code con PKCE.
- **Indirizzi dall'issuer**: `authorizationUrl` e `tokenUrl` sono `authorization_endpoint` e
  `token_endpoint` del documento di discovery. Nessun indirizzo di Entra è scritto nel codice, quindi
  l'issuer resta un OIDC generico (ADR 0016). La lettura passa dalla stessa funzione HTTPS, con lo stesso
  timeout, usata per le chiavi. Un indirizzo che non è HTTPS viene rifiutato.
- **Lettura al primo uso, ricordata dopo il primo successo**: la discovery si legge quando la pagina chiede
  il documento OpenAPI, non all'avvio.
- **Issuer irraggiungibile**: l'API parte comunque. Le funzioni protette restano chiuse come prima, perché i
  token non si possono verificare. Il documento OpenAPI risponde 503 "directory non raggiungibile" e non
  ricorda il fallimento: la richiesta successiva riprova, e la pagina mostra il login appena l'issuer
  risponde.
- **Scope**: lo schema dichiara `AUTH_SCOPE`, che la pagina chiede al login.
- **Come**: il documento OpenAPI di FastAPI si estende sostituendo `app.openapi`, come prevede la
  documentazione di FastAPI. La dipendenza di sicurezza del router protetto resta un semplice lettore del
  token Bearer; la verifica resta in `current_user`.

## Alternative scartate

- **`OAuth2AuthorizationCodeBearer` costruito all'avvio**: vuole gli indirizzi alla costruzione. Servirebbe
  leggere la discovery all'avvio, e con l'issuer irraggiungibile l'API non partirebbe o partirebbe senza
  login fino al riavvio.
- **Indirizzi scritti nella configurazione**: due variabili in più per ogni installazione, che possono
  andare fuori allineamento con l'issuer.
- **Restare su `openIdConnect`**: la pagina continua a offrire il flusso implicito.

## Conseguenze

- La pagina offre un solo login, Authorization Code con PKCE.
- La prima apertura della pagina fa una richiesta all'issuer; le successive no.
- Se l'issuer non risponde, la pagina non si carica finché non torna raggiungibile. Le funzioni protette
  erano già chiuse in quel caso.
