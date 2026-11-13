# ADR 0100 — La configurazione la legge ogni adapter dalla sua sorgente

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.1.4, R0.2.1 (ambiente e rete dell'installazione); Bug B0.0.3 (177), categoria D
- Supera: ADR 0015 nella parte in cui `bootstrap.py` legge le variabili e i file dei segreti e li passa ai
  costruttori; il vincolo dei segreti solo in file montati resta
- Collegate: ADR 0007 (chiavi delle credenziali), ADR 0021 (worker e token della macchina), ADR 0035 (bot),
  ADR 0087 (rete dell'installazione), ADR 0089 (niente ponti), CLAUDE.md (Regola delle dipendenze)

## Contesto e problema

`bootstrap.py` leggeva la configurazione da sé: un dizionario dell'ambiente, i nomi delle variabili, i default
(porta 5432, versione della chiave 1, slippage 5%), le funzioni `_required`, `_secret`, `_optional_secret`,
`_environment`, la decodifica base64 delle chiavi, gli errori di configurazione e due contenitori
(`PublicCredentialsKey`, `WorkerSettings`). Erano decisioni e costanti nel composition root, che deve solo
collegare, e ogni nuova tecnologia avrebbe aggiunto altre righe di lettura nello stesso file.

Il proprietario indica il modello dei suoi progetti .NET: una `IConfiguration` unica, una classe interna
`{Tech}Configurations` per libreria e un metodo di estensione `Add{X}(this IServiceCollection, IConfiguration)`
che legge la sua sezione e registra i servizi pronti.

## Decisione

- **Sorgente unica**: `adapters/configuration/source.py` definisce `ConfigurationSource`, l'unico codice che legge
  l'ambiente del processo (`PROCESS_ENVIRONMENT`) e i file dei segreti. Metodi `value`, `optional`, `secret`,
  `optional_secret` (il segreto `X` è il contenuto del file indicato da `X_FILE`) ed `environment()`.
  `MissingConfigurationError` e `InvalidConfigurationError` stanno in `adapters/configuration/errors.py` con gli
  stessi messaggi e lo stesso attributo `name` di prima.
- **Impostazioni per cartella** (l'equivalente di `{Tech}Configurations`): `configuration.py` di ogni cartella
  adapter con configurazione definisce una dataclass frozen privata `_<Tecnologia>Settings` e la funzione privata
  che la legge, applica i default e valida forma e presenza. Cartelle toccate: `sqlalchemy` (database),
  `libsodium` (chiave pubblica o privata e versione), `oidc` (issuer e audience), `worker` (indirizzo e token del
  worker), `telegram` (token del bot, che c'era già come impostazione privata), `hyperliquid` (slippage degli
  ordini a mercato, accanto alla rete che c'era già), `litellm` (indirizzo del proxy e master key, ADR 0101), `inbound/api` (versione, client del login, token del worker).
- **Composizione per cartella** (l'equivalente di `Add{X}`): `composition.py` espone `<tecnologia>_adapters(source,
  ...)`, che restituisce adapter pronti: `sqlalchemy_adapters` (engine), `libsodium_sealing_adapters` (sigillatori
  legati al tenant), `libsodium_opening_adapters`, `oidc_adapters` (o `None` senza issuer),
  `worker_adapters` e `telegram_adapters` (ora ricevono la sorgente invece di indirizzo e token),
  `hyperliquid_slippage_adapters`, `litellm_adapters`, `api_adapters`, `worker_api_adapters`.
- **Regole di business nel domain**: gli ambienti ammessi diventano `InstallationEnvironment` in
  `domain/accounts/installation_environment.py`, accanto a `ExchangeNetwork.of_installation`, con
  `UndeclaredEnvironmentError` e `UnsupportedEnvironmentError` negli errori del contesto; la slippage resta
  `Slippage.percent`.
- **bootstrap.py** crea `ConfigurationSource(configuration)` e la passa solo alle funzioni `*_adapters`; le
  firme delle factory di uvicorn restano (`configuration: Mapping[str, str] = PROCESS_ENVIRONMENT`), quindi
  Dockerfile e compose non cambiano. Non contiene più nomi di variabili, default, errori di configurazione,
  `PublicCredentialsKey` e `WorkerSettings`: `worker_use_cases` e `cycle_ports` ricevono ambiente e slippage.
- **Test di architettura** nuovi, ciascuno con esempio violato e conforme: `configurazione-solo-dalla-sorgente`,
  `impostazioni-nella-loro-cartella`, `bootstrap-configura-solo-con-composizioni`. Contratto import-linter: la
  sorgente non importa le cartelle di tecnologia né application.

## Alternative scartate

- **Una `Settings` globale (pydantic-settings) letta all'avvio**: una libreria nuova, un oggetto che conosce
  tutte le tecnologie e impostazioni come stato di modulo; contraria a «un adapter = una tecnologia».
- **Il costruttore di ogni adapter riceve la sorgente**: ogni adapter dipenderebbe dalla configurazione e i test
  degli adapter dovrebbero costruirla; il costruttore riceve invece valori tipizzati o client.
- **Funzioni `configure_<x>` in `bootstrap.py`**: lascerebbero nomi e default nel composition root.

## Confronto con le decisioni scritte

- CLAUDE.md, «Regola delle dipendenze»: «Le cartelle `adapters/<verso>/<tecnologia>` non si importano a vicenda».
  `adapters/configuration` non è una cartella di tecnologia (è sotto `adapters/`, non sotto un verso) e la
  importano solo `configuration.py` e `composition.py`: è l'eccezione per nome autorizzata dal proprietario,
  scritta in CLAUDE.md e nei contratti; conforme.
- CLAUDE.md, «Sicurezza»: «Mai segreti in variabili d'ambiente: solo file montati in sola lettura». `secret` legge
  solo il file indicato da `<NOME>_FILE`; conforme.
- CLAUDE.md, «Test di architettura»: «nessuna regola ha eccezioni per nome». La sorgente è un'eccezione alla
  separazione delle cartelle, non a una regola: le tre regole nuove non hanno voci in `known_violations.py`.
- `.claude/rules/layer-adapters.md`: «Configurazione e segreti arrivano dal costruttore; un adapter non legge
  variabili d'ambiente». Riscritta: il costruttore riceve impostazioni tipizzate; la lettura avviene in
  `configuration.py` attraverso la sorgente, mai dall'ambiente.
- `docs/architecture.md` (segreti come file montati, compose invariato): conforme.

## Scostamenti

- **`bootstrap.py` legge `source.environment()`**: l'ambiente dell'installazione serve, come valore, a casi d'uso
  e porte che `bootstrap.py` compone ancora (rete degli exchange in `hyperliquid_adapters(network)`,
  `TenantPorts.environment`, verifica e registro del ciclo).
  È l'equivalente di `IHostEnvironment` in .NET, dato dall'host e non da una libreria; la regola lo ammette per
  nome e nessun'altra lettura.
- **Gli adapter legati al tenant si costruiscono ancora in `bootstrap.py`** (`for_tenant`): «bootstrap chiama
  solo le funzioni `*_adapters`» è applicato alla configurazione, cioè la sorgente va solo a quelle funzioni.
  Spostare la costruzione per tenant nelle cartelle è il lavoro della categoria E del Bug 177.
- **`hyperliquid_slippage_adapters` restituisce una `Slippage` di dominio, non un adapter**: la slippage è un
  parametro degli ordini a mercato verso l'exchange, ma i casi d'uso degli ordini la ricevono già come argomento
  (`OpenPositionUseCase`, `CloseExchangePositionUseCase`, `ExecuteFlowOrdersUseCase`). Darla in costruzione
  all'adapter degli ordini cambierebbe il contesto `orders`, fuori dal perimetro della categoria D; il nome
  segue la convenzione `*_adapters` perché solo queste funzioni ricevono la sorgente.
- **Cartelle senza configurazione d'installazione** (`alternative_me`, `coinmarketcap`, `rss`): le loro funzioni
  `*_adapters` non ricevono la sorgente, perché non leggono nulla dall'installazione; i loro `configuration.py`
  tengono solo i valori fissi della tecnologia.

## Conseguenze

- Cambiano due comportamenti marginali, in meglio: un file di segreto che non esiste è
  `MissingConfigurationError` invece di un `FileNotFoundError` di sistema; `DATABASE_PORT` e
  `CREDENTIALS_KEY_VERSION` non numerici sono `InvalidConfigurationError` invece di un `ValueError`.
- Una tecnologia nuova aggiunge il suo `configuration.py` e il suo `composition.py`; `bootstrap.py` aggiunge una
  chiamata.
- Voci tolte da `known_violations.py`: le funzioni di lettura (`_authentication`, `_credentials_private_key`,
  `_credentials_public_key`, `_environment`, `_optional_secret`, `_required`, `_secret`, `slippage_from`), le
  costanti (`DEFAULT_CREDENTIALS_KEY_VERSION`, `DEFAULT_DATABASE_PORT`, `HYPERLIQUID`, `SLIPPAGE_SETTING`,
  `SUPPORTED_ENVIRONMENTS`, `TELEGRAM_BOT_SETTING`), le classi (`InvalidConfigurationError`,
  `MissingConfigurationError`, `PublicCredentialsKey`, `UndeclaredEnvironmentError`,
  `UnsupportedEnvironmentError`, `WorkerSettings`) e l'import di `os`.
