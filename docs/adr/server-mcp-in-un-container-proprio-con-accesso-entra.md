# ADR server-mcp-in-un-container-proprio-con-accesso-entra — Server MCP in un container proprio, con accesso Entra e le operazioni dell'API sui flussi

- Stato: proposta (24 novembre 2026); la parte «Autenticazione» (registrazione del client e identificativi dell'applicazione dell'API) è sostituita dall'ADR impostazioni-entra-dell-accesso-mcp-riproducibili (25 novembre 2026)
- Requisiti: US 527 R6.6.1 (Task 528, 529)
- Collegate: ADR 0013 (installazioni raggiungibili solo via Tailscale), ADR 0016 (autenticazione OIDC), ADR 0027
  (errori in Problem Details), ADR 0116 e 0117 (container della dashboard sul suo percorso), ADR 0118 (accesso Entra
  come SPA con PKCE); `.claude/rules/layer-adapters.md`, `.claude/rules/tech-fastapi.md`, `.claude/rules/tech-oidc.md`,
  `.claude/rules/context-tenancy.md`, `.claude/rules/ci.md`, `.claude/rules/specs.md`
- Verifica: prova

## Contesto e problema

R6.6.1 vuole che l'utente consulti e gestisca i suoi flussi da un client IA che parla MCP (Model Context Protocol),
senza aprire la dashboard, con gli stessi casi d'uso e le stesse regole dell'API, solo dalla tailnet e solo sui dati
del suo tenant. Servono libreria, trasporto, autenticazione secondo la specifica MCP con Entra, collocazione nel
deploy ed elenco degli strumenti.

## Fattori decisionali

- Decisioni del proprietario (24 novembre 2026, in chat):
  - container proprio, non dentro `api`;
  - gli strumenti fanno anche tutte le operazioni sui flussi che l'API espone, non solo letture;
  - client preregistrato in una registrazione Entra nuova, creata come la prima (`autotrading-dev`, a mano e
    descritta nelle ADR: non c'è uno script versionato che la crei);
  - valgono solo i client che girano su un dispositivo della tailnet; nessuna esposizione su internet.
- `CLAUDE.md`: un adapter = una tecnologia, una libreria in una sola cartella; il caso d'uso orchestra; l'adapter in
  ingresso chiama i casi d'uso legati al tenant come il router FastAPI; `bootstrap.py` compone senza decisioni;
  configurazione per adapter; segreti solo da file montati; deploy solo dalla pipeline.
- Specifica MCP (autorizzazione): su HTTP il server è un OAuth 2.1 resource server, pubblica i Protected Resource
  Metadata (RFC 9728) e risponde 401 con `WWW-Authenticate` che li indica; non emette token.
- Entra non supporta la registrazione dinamica dei client: il client MCP usa un client id preregistrato. Il token
  Entra ha come audience l'applicazione dell'API, non l'URL del server.

## Decisione

### Libreria e trasporto

- Libreria ufficiale MCP per Python (`mcp`, ultima versione stabile pubblicata da almeno due settimane), importata solo
  nella nuova cartella `src/autotrading/adapters/inbound/mcp/`, che la dichiara come sua libreria. Il server usa la
  classe server alta dell'SDK con gli strumenti dichiarati per funzione.
- Trasporto Streamable HTTP sul percorso `/mcp`, senza stato di sessione lato server (ogni richiesta porta il token).

### Container e rete

- Nuovo servizio `mcp` in `deploy/compose.yaml`: stessa immagine di `api` e `worker`, comando
  `autotrading.bootstrap:create_mcp_application --factory` su porta 8000 nel container, pubblicato solo su
  `127.0.0.1:8090`, utente non privilegiato, filesystem in sola lettura, healthcheck su `/health`, stessa rete e stessa
  configurazione di database e OIDC di `api` (nessun segreto nuovo; nessun accesso alla chiave privata delle
  credenziali, che resta solo al `worker`).
- Tailscale Serve espone `http://127.0.0.1:8090/mcp` sul percorso `/mcp` dello stesso nome HTTPS dell'API, in
  `deploy/cloud-init.yaml` e in `deploy/configure-serve.sh` accanto a `/dashboard` (ADR 0117). Raggiungibile solo dalla
  tailnet (ADR 0013).
- `bootstrap.create_mcp_application` compone l'applicazione con le stesse funzioni `*_adapters` e gli stessi casi
  d'uso per tenant che usa `create_application`, senza decisioni.

### Autenticazione

- Il server è solo resource server: un `TokenVerifier` dell'adapter `mcp/` riceve `AccessTokenVerifierPort` (la porta
  che già usa l'API, realizzata da `OidcAccessTokenVerifierAdapter`) e `ResolveTenantUseCase`. Token non valido,
  scaduto o di un'altra audience: 401 con `WWW-Authenticate` verso i metadati. Token valido senza il ruolo Utente:
  rifiuto come nell'API (403). Il tenant si risolve dall'`oid` come nell'API e gli strumenti girano sulle porte legate a
  quel tenant (RLS).
- Metadati RFC 9728 pubblicati dall'SDK: `authorization_servers` è l'issuer Entra già configurato per l'API,
  `resource` è l'URL pubblico `https://<nome>/mcp` (variabile `MCP_PUBLIC_URL` nel `configuration.py` di `mcp/`),
  `scopes_supported` è lo scope dell'API (`api://<client id dell'API>/access`). La verifica della risorsa del token
  resta spenta (`validate_token_resource` falso): Entra lega il token all'applicazione dell'API, e l'audience la
  controlla già l'adapter OIDC.
- Client: registrazione Entra `autotrading-mcp-dev` (client id `ef23ec9e-7d53-48f9-be29-6876e470283d`), client
  pubblico con redirect `http://localhost` (qualunque porta, come Entra ammette per i client nativi), PKCE, permesso
  delegato sullo scope `access` di `autotrading-dev`. Creata il 24 novembre 2026 con `az ad app create` dall'identità
  del proprietario. Il ruolo Utente resta quello dell'applicazione dell'API: chi non lo ha è rifiutato. Prod avrà la
  sua registrazione quando prod verrà attivato (come ADR 0118).

### Strumenti

- Uno strumento per ciascuna lettura e ciascuna operazione sui flussi dell'API, sopra lo stesso caso d'uso con lo
  stesso comando, nomi inglesi in snake_case e descrizione in italiano:
  - letture: elenco dei flussi (stato, valore, PnL dall'avvio), dettaglio e stato di un flusso, posizioni aperte e
    chiuse, cicli e decisioni di un ciclo, statistiche e risultati, classifica dei flussi, conti (senza credenziali);
  - operazioni: crea, importa, duplica, modifica, avvia e pausa, ferma, archivia, incassa, cambia capitale assegnato,
    ciclo a richiesta, riprendi aperture.
- Nessuno strumento legge, registra, ruota o cancella credenziali di conti, fonti o fornitori IA, e nessuno espone
  chiavi o segreti. Un test di architettura lo verifica sull'elenco degli strumenti.
- Gli strumenti ricevono e restituiscono modelli tipizzati dell'adapter `mcp/` (non quelli di `adapters/inbound/api/`,
  perché le cartelle adapter non si importano). Un errore del progetto diventa un risultato d'errore dello strumento
  con il suo messaggio, lo stato e i `details` dell'errore (ADR 0027): stesse regole, stessa risposta dell'API.

### Prove

- Nuovo sistema `mcp` negli scenari: `specs/E6-piattaforma-e-operativita/F6.6-server-mcp/R6.6.1-.../mcp/*.feature`,
  eseguiti con il client MCP dell'SDK sull'applicazione in memoria (adapter finti, verificatore di token finto).
- Unit test dell'adapter (verificatore, traduzione degli errori, ogni strumento) e test di architettura sulla
  libreria `mcp` confinata in `adapters/inbound/mcp/` e sull'assenza di strumenti sulle credenziali.
- Integrazione: l'applicazione `mcp` contro PostgreSQL con un tenant e RLS, come i test dell'API.

## Alternative scartate

- **Server dentro `api` su `/mcp`**: un container in meno, ma il proprietario vuole un container proprio.
- **Solo letture**: era il requisito iniziale; il proprietario vuole anche le operazioni sui flussi.
- **Esposizione su internet (Tailscale Funnel) per i connettori di claude.ai**: viola ADR 0013 e il requisito.
- **Server MCP che emette token o fa da proxy OAuth verso Entra**: più superficie e segreti; la specifica ammette il
  resource server puro con un client preregistrato.
- **Riuso della registrazione SPA della dashboard**: mescola un client browser e un client nativo nella stessa
  registrazione.
- **Trasporto stdio**: richiede il processo sul dispositivo dell'utente con accesso diretto al database; escluso.

## Conseguenze

- Un container in più nelle installazioni, e un percorso in più in Tailscale Serve.
- Una libreria nuova (`mcp`) nel progetto, confinata in una cartella, con la sua rule `.claude/rules/tech-mcp.md`
  (percorso `adapters/inbound/mcp/**`) aggiunta all'indice delle rule e alla struttura in `CLAUDE.md`.
- Il client si configura con l'URL `https://<nome>/mcp` e il client id della registrazione `autotrading-mcp-dev`.
- Ogni nuova operazione sui flussi dell'API va esposta anche come strumento MCP, o dichiarata esclusa.
