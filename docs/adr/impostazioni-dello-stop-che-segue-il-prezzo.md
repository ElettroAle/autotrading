# ADR impostazioni-dello-stop-che-segue-il-prezzo — Impostazioni dello stop che segue il prezzo nella configurazione del flusso

- Stato: accettata (26 novembre 2026)
- Requisiti: US 749 R5.5.1 (Task 750)
- Collegate: ADR stop-loss-e-take-profit-predefiniti-del-flusso, ADR 0051 (porta al minimo nella configurazione),
  ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione; `.claude/rules/context-flows.md`,
  `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-fastapi.md`, `.claude/rules/tech-mcp.md`
- Verifica: prova

## Contesto e problema

R5.5.1 chiede quattro impostazioni facoltative del flusso: distanza dello stop che segue (0,1-50%), attivazione (> 0,
solo con la distanza), pareggio (> 0, indipendente) e l'opzione del massimo profitto raggiunto nel contesto
dell'agente (spenta). Tutte vuote o spente di default; con il default il flusso si comporta come oggi.

## Fattori decisionali

- Requisito R5.5.1 del proprietario e i suoi criteri (motivi di rifiuto letterali).
- Ordine del proprietario per F5.5 (26 novembre 2026): impostazioni generiche, facoltative, vuote o spente di default;
  i flussi esistenti non ricevono una versione nuova della configurazione.
- Le protezioni predefinite vivono già in `ProtectionDefaults` della configurazione versionata (ADR
  stop-loss-e-take-profit-predefiniti-del-flusso); una modifica crea una versione (R1.1.3).
- `CLAUDE.md`: regole sui valori nel domain; un solo tipo di richiesta condiviso da API e MCP; nessuna duplicazione.

## Decisione

- **Domain.** Un value object `TrailingStop` (distanza, attivazione, pareggio, massimo profitto nel contesto) nella
  `FlowConfiguration`, accanto a `ProtectionDefaults`, con le invarianti e i loro errori di dominio tipizzati (come gli
  altri errori di configurazione), con i motivi dei criteri: «la distanza dello stop che segue va da 0,1 a 50»,
  «l'attivazione richiede la distanza dello stop che segue», «l'attivazione dello stop che segue è maggiore di 0», «il
  pareggio è maggiore di 0». Senza distanza e senza pareggio lo stop che segue non è attivo. `TrailingStop()` è il
  default: tutto vuoto, opzione spenta.
- **Configurazione versionata.** Le parti si salvano con la versione come le altre; voci `FlowSetting` e righe del
  confronto delle versioni; creazione, modifica, rimozione (le parti che si possono togliere con i flag `remove_*` come
  le altre), documento di strategia (esportazione e importazione), API e strumenti MCP con lo stesso tipo di richiesta
  condiviso.
- **Migrazione.** Parti facoltative con il default vuoto: le versioni esistenti le leggono vuote, nessuna versione
  nuova.

## Alternative scartate

- **Impostazioni dentro `ProtectionDefaults`**: mescola le protezioni all'apertura con il loro movimento e allarga
  invarianti già provate.
- **Impostazioni per posizione decise dall'agente**: fuori ambito nel requisito.

## Conseguenze

- Un flusso senza le impostazioni resta identico, configurazione compresa.
