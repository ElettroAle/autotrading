# ADR impostazioni-entra-dell-accesso-mcp-riproducibili — Impostazioni Entra dell'accesso MCP in uno script del proprietario

- Stato: proposta (25 novembre 2026)
- Requisiti: Bug 738 (padre US 527 R6.6.1), Task 739
- Sostituisce: la parte «Autenticazione» dell'ADR server-mcp-in-un-container-proprio-con-accesso-entra (registrazione
  del client e identificativi dell'applicazione dell'API); il resto di quell'ADR resta in vigore
- Collegate: ADR 0013 (installazioni raggiungibili solo via Tailscale), ADR 0016 (autenticazione OIDC), ADR 0118
  (accesso Entra come SPA con PKCE); `.claude/rules/ci.md`, `.claude/rules/tech-mcp.md`, `.claude/rules/tests.md`
- Verifica: prova

## Contesto e problema

Il 24 novembre 2026 l'accesso di Claude Code al server MCP di dev è fallito due volte con Entra:

1. `AADSTS9010010`: come vuole la specifica MCP (RFC 8707), il client invia come `resource` l'URL pubblico
   `https://<nome>/mcp` che i metadati RFC 9728 del server dichiarano. Entra v2 accetta `resource` solo se è un
   identificativo dell'applicazione a cui appartiene lo scope richiesto (`api://<client id dell'API>/access`), e
   l'applicazione dell'API aveva solo `api://<client id>`.
2. `AADSTS50011`: Claude Code riceve il codice su `http://localhost:<porta>/callback`; il client MCP registrava
   `http://localhost` senza percorso. Per i client nativi Entra ignora la porta di localhost, non il percorso.

Il proprietario ha corretto le due impostazioni a mano in dev. Nel repository non sono scritte da nessuna parte: prod
nascerebbe con lo stesso difetto. Va deciso dove si dichiarano e chi le applica.

## Fattori decisionali

- Decisione del proprietario (24-25 novembre 2026, in chat): le impostazioni si dichiarano nel repository in uno
  script `az` idempotente in `deploy/`, lanciato dal proprietario una volta per installazione con la sua identità;
  la pipeline non tocca Entra, perché l'identità di deploy non deve poter modificare applicazioni Entra (un workflow
  compromesso potrebbe cambiare redirect e identificativi e dirottare l'accesso alla piattaforma).
- `CLAUDE.md`, «Sicurezza»: mai token personali, solo `az` con l'identità dell'utente; il deploy passa sempre dalla
  pipeline. Lo script non è un deploy: configura la directory, come la registrazione a mano dell'ADR 0016.
- ADR 0005 e ADR 0008: niente Terraform per l'infrastruttura (backend di stato eccessivo).
- ADR server-mcp-in-un-container-proprio-con-accesso-entra: il server resta solo resource server, i metadati
  RFC 9728 dichiarano come risorsa l'URL pubblico `/mcp`, la verifica della risorsa del token resta spenta (Entra lega
  il token all'applicazione dell'API, l'audience la controlla l'adapter OIDC). Queste parti non cambiano.

## Opzioni considerate

### 1. Script `az` idempotente in `deploy/entra/`, lanciato dal proprietario

- Pro: impostazioni versionate e riproducibili; nessun permesso Entra nuovo alla pipeline; rilanciarlo non cambia
  nulla se è già tutto in ordine.
- Contro: è un passo manuale per installazione, da ricordare all'attivazione di prod.

### 2. Passo della pipeline con un'identità che può modificare le applicazioni Entra

- Pro: nessun passo manuale.
- Contro: dà alla pipeline `Application.ReadWrite` sulla directory, contro la decisione del proprietario; allarga la
  superficie di un workflow compromesso a tutto l'accesso della piattaforma.

### 3. Metadati RFC 9728 con risorsa `api://<client id>` al posto dell'URL pubblico

- Pro: nessuna modifica all'applicazione dell'API.
- Contro: la specifica MCP chiede che la risorsa dei metadati coincida con l'URL del server; i client conformi la
  verificano e rifiutano il server.

### 4. Solo documentazione nell'ADR, come per le registrazioni precedenti

- Pro: nessun codice nuovo.
- Contro: è ciò che ha prodotto il difetto: le impostazioni descritte a parole non si verificano e si dimenticano.

## Esito della decisione

Scelta: **opzione 1**. È l'unica che rende le impostazioni verificabili senza dare alla pipeline poteri sulla
directory.

- `deploy/entra/configure-mcp-access.sh`, bash, eseguito dal proprietario sul suo PC con `az` già autenticato (profilo
  isolato, `AZURE_CONFIG_DIR` impostato da lui), con tre argomenti: client id dell'applicazione dell'API, client id
  del client MCP, nome HTTPS dell'installazione. Nessun segreto, nessun default legato al nome dell'installazione.
- Applicazione dell'API: legge `identifierUris` e, se manca, aggiunge `https://<nome>/mcp` conservando quelli
  presenti (`api://<client id>` compreso). Se c'è già, non scrive.
- Client MCP: imposta come unico redirect dei client pubblici `http://localhost/callback`. Se è già così, non scrive.
- Stampa in italiano che cosa ha cambiato o che era tutto in ordine; esce con errore su argomenti mancanti o su un
  errore di `az`.
- In dev le impostazioni sono già state applicate a mano il 24 novembre 2026: lo script rilanciato non cambia nulla.
  Per prod si lancia all'attivazione, accanto alla sua registrazione (ADR 0118).

### Conseguenze

- Le prove in `tests/unit/deploy/` eseguono lo script con un `az` finto in testa al `PATH`, che registra le chiamate
  e restituisce stati preparati: aggiunta dell'identificativo mancante, redirect corretto, nessuna scrittura su
  un'installazione già configurata, errore senza argomenti. Il loro nome cita questa ADR.
- Una prova di architettura verifica che nessun workflow in `.github/` né altro script di `deploy/` invochi
  `az ad app`: Entra resta fuori dalla pipeline.
- L'ADR server-mcp-in-un-container-proprio-con-accesso-entra dichiara nello stato di essere sostituita in parte da
  questa.

## Ulteriori informazioni

- Bug: [#738 - Accesso al server MCP da Claude Code rifiutato da Entra]
- Specifica MCP, autorizzazione: RFC 9728 (Protected Resource Metadata) e RFC 8707 (Resource Indicators)
