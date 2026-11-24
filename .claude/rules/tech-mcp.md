---
paths:
  - "src/autotrading/adapters/inbound/mcp/**"
  - "tests/unit/adapters/mcp/**"
  - "tests/scenarios/E6-piattaforma-e-operativita/F6.6-server-mcp/**"
  - "specs/E6-piattaforma-e-operativita/F6.6-server-mcp/**"
---

# Adapter in ingresso: server MCP

Decisione in `docs/adr/server-mcp-in-un-container-proprio-con-accesso-entra.md`.

- Il sistema integrato è il Model Context Protocol: la libreria ufficiale `mcp` si importa solo qui, con la classe
  server alta (`MCPServer`) e gli strumenti dichiarati per funzione. Trasporto Streamable HTTP su `/mcp`, senza stato
  di sessione, risposte JSON; `/health` per il controllo del container.
- Il server è solo resource server: non emette token. `TenantTokenVerifier` verifica il token Entra con
  `AccessTokenVerifierPort`, la stessa porta dell'API: un token rifiutato risponde 401 con `WWW-Authenticate` verso i
  metadati RFC 9728 (issuer Entra dell'API, risorsa `MCP_PUBLIC_URL`, scope dell'API); un token senza il ruolo Utente
  non riceve lo scope della piattaforma e risponde 403, senza tenant creato (R0.1.1). Il tenant si risolve dall'`oid`
  con `ResolveTenantUseCase`.
- Uno strumento per ciascuna lettura e operazione sui flussi dell'API, sullo stesso caso d'uso con lo stesso comando;
  i casi d'uso arrivano in `McpUseCases`, presi da `bootstrap.mcp_use_cases` tra quelli che l'API costruisce per il
  tenant della richiesta. Nomi inglesi in snake_case, descrizione in italiano.
- Nessuno strumento legge, registra, ruota o cancella credenziali di conti, fonti o fornitori IA, e nessuno espone
  chiavi o segreti (verificato in `tests/architecture/`).
- Gli strumenti ricevono dataclass dell'adapter e restituiscono viste dataclass con i campi e i testi dell'API (importi
  come testi, ADR 0018; istanti ISO 8601 in UTC con `Z`). Le cartelle adapter non si importano: nessun modello di
  `adapters/inbound/api/` qui.
- Un errore del progetto diventa un risultato d'errore dello strumento con `type`, `title`, `status`, `detail` e i
  `details` dell'errore (ADR 0027); ogni altra eccezione resta il fallimento generico del server, che non ne mostra il
  testo.
- Ogni nuova operazione sui flussi dell'API va esposta anche come strumento, o dichiarata esclusa.
