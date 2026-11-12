# ADR 0031 — Creazione di un flusso: configurazione versionata, verificata dai contesti che la conoscono

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.1.1 (Task T1.1.1.2), con R1.4.1 e R1.4.2 per il modello del flusso

## Contesto

R1.1.1 chiede di creare un flusso di trading con la configurazione completa: nome, conto, asset, intervallo di
ciclo, modello IA con i parametri, fonti con pesi e parametri, istruzioni, limiti di rischio, capitale
allocato. Una configurazione non valida è rifiutata per intero, con il motivo; un flusso nuovo è fermo. Il
capitale allocato non supera il capitale libero del conto, cioè il saldo letto dall'exchange meno le
allocazioni degli altri flussi del conto. R1.4.1 vuole che il modello sia di un fornitore di cui l'utente ha
registrato la chiave, e che la rimozione di una chiave usata da flussi attivi o in pausa sia rifiutata; R1.4.2
che i parametri del modello siano tra quelli ammessi, con i predefiniti per gli altri.

Ogni pezzo della configurazione appartiene a un contesto diverso (ADR 0026): il conto e il suo saldo ad
`accounts`, il modello e le chiavi ad `agent`, le fonti a `sources`, gli asset negoziabili all'exchange.
Il contesto `flows` non può importare nessuno di loro.

## Decisione

- **Domain di `flows`**: `Flow` (`TenantOwned`: conto, nome, stato, configurazione in vigore),
  `FlowConfiguration` immutabile e numerata (la prima è la versione 1), `FlowStatus` (`fermo`, `attivo`,
  `in pausa`, `archiviato`), `CycleInterval` (1-1440 minuti, 15 se non indicato), `RiskLimits` (leva massima
  obbligatoria, almeno un'esposizione per operazione, nessun predefinito), `ModelSelection` e
  `SourceSelection` (peso 1-10, 5 se non indicato), `FreeCapital`. Ogni regola che non dipende da altri
  contesti si verifica qui, con un errore tipizzato che porta il motivo dello scenario.
- **Un caso d'uso, controlli nominati in ordine**: `CreateFlowUseCase` verifica nome, nome libero,
  configurazione (che chiede modello e fonti ai rispettivi contesti), conto, asset negoziabili, capitale
  libero; poi salva. Il primo motivo trovato è quello della risposta; nulla si salva se un controllo fallisce.
- **Porte di `flows` e bridge in `bootstrap.py`**, come per ordini e verifica (ADR 0023, ADR 0024):
  - `FlowAccountPort` ← `FlowAccountsFromAccounts`: cerca il conto del tenant e ne legge il saldo dal
    `worker` (R0.2.2); un conto di un altro tenant non è trovato (R0.1.3).
  - `ModelSettingsPort` ← `ModelSettingsFromAgent`: modello del catalogo, poi parametri ammessi con i
    predefiniti, poi chiave del fornitore registrata; il rifiuto arriva al flusso con il motivo di `agent`
    (`InvalidFlowSettingError`, 422).
  - `SourceSettingsPort` ← `SourceSettingsFromSources`: fonte del catalogo, parametri interi nei limiti con i
    predefiniti (`SourceDefinition.settings`).
  - `MarketsPort` ← `HyperliquidMarketsAdapter`: gli asset elencati, e non ritirati, nei metadati pubblici di
    Hyperliquid, sulla rete dell'installazione; nessuna credenziale, quindi lo legge l'API.
  - `ProviderKeyUsagePort` di `agent` ← `ProviderKeyUsageFromFlows`, che sostituisce il bridge provvisorio di
    ADR 0029: una chiave è usata dai flussi attivi o in pausa con un modello del suo fornitore.
- **Persistenza**: tabella `flows` (stato, nome unico tra i flussi non archiviati del tenant con un indice
  parziale, conto dello stesso tenant per chiave esterna composta) e tabella `flow_versions` (una riga per
  versione, configurazione in JSONB con importi e parametri come testo). Row level security su entrambe come
  `accounts` (ADR 0018); il ruolo applicativo può solo inserire e leggere le versioni, mai cambiarle o
  cancellarle, perché ogni ciclo deve poter essere ricostruito con la versione che ha usato (R1.1.3).
  Migrazione 0008.
- **API**: `POST /flows` (201), `GET /flows`, `GET /accounts/{account_id}/free-capital`. Importi e parametri
  numerici viaggiano come stringhe (ADR 0018).

## Alternative scartate

- **Configurazione in colonne**: ogni fonte e ogni parametro nuovo cambierebbe lo schema; la versione è un
  documento immutabile che si legge sempre per intero.
- **Versioni nella stessa riga del flusso**: una modifica sovrascriverebbe la configurazione usata dai cicli
  passati, contro R1.1.3.
- **Capitale libero salvato**: il saldo cambia sull'exchange; letto al momento della creazione, non invecchia
  mai.
- **Asset negoziabili dal catalogo statico**: Hyperliquid aggiunge e ritira mercati; i metadati pubblici
  sono la fonte vera e non chiedono credenziali.
- **`flows` che chiama i casi d'uso degli altri contesti**: romperebbe l'indipendenza dei contesti
  verificata da import-linter; i bridge in bootstrap sono il punto previsto per collegarli.

## Conseguenze

- La creazione legge il saldo dal `worker` e i mercati da Hyperliquid: se uno dei due non risponde, la
  creazione risponde 503 e non salva nulla.
- La regola di conflitto sugli asset (R1.1.2), la modifica versionata (R1.1.3) e i cambi di stato
  (R1.1.4-R1.1.6) si appoggiano sulle stesse tabelle. Lo scenario di R1.4.1 sulla rimozione rifiutata resta
  `@wip` finché un flusso non si può avviare (R1.1.4).
- Gli scenari usano nomi brevi di modello (`openrouter/deepseek-chat`) che il catalogo vero non ha: il test
  li aggiunge al catalogo della piattaforma finta, come fa R1.4.2.
