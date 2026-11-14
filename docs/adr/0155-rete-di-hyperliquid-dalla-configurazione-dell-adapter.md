# ADR 0155 — Rete di Hyperliquid dalla configurazione dell'adapter

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: Bug 277 (Task 278), R0.2.1
- Collegate: ADR 0126 (ne sostituisce la regola di rete: `ExchangeNetwork.of_installation`), ADR 0087, ADR 0015

## Contesto e problema

La rete di Hyperliquid si deduceva dal nome dell'installazione (`ExchangeNetwork.of_installation`: `dev` = testnet,
altrimenti mainnet). L'adapter non era configurabile e il domain conosceva il nome `dev`: un'installazione dev su
mainnet, o prod su testnet, chiedeva una modifica del codice.

## Opzioni considerate

### 1. Variabile `HYPERLIQUID_NETWORK` letta dall'adapter

- Pro: configurazione normale, come ogni altro adapter; il domain non conosce le installazioni.
- Contro: una variabile in più da dichiarare per installazione.

### 2. Rete come attributo del conto

- Pro: test e reale nella stessa installazione.
- Contro: migrazione dei dati, cambia R0.2.1, rischio di confondere un conto reale con uno di prova.

### 3. Deduzione dal nome dell'installazione

- Pro: nessun lavoro.
- Contro: è il difetto.

## Esito della decisione

Opzione 1. `adapters/outbound/hyperliquid/configuration.py` legge `HYPERLIQUID_NETWORK`, obbligatoria e senza default,
con i nomi che Hyperliquid dà alle sue reti: `testnet` o `mainnet` (maiuscole e spazi ignorati). Assente: il servizio
non parte (`MissingConfigurationError`); un altro valore: `InvalidConfigurationError`. `hyperliquid_adapters(source)`
riceve la `ConfigurationSource` e `bootstrap.py` crea gli adapter una volta per servizio, passandoli ai casi d'uso.

`ExchangePort.is_real()` dice se l'adapter opera sulla rete del denaro reale; `ListAccountsUseCase` e
`GetAccountUseCase` ricavano la rete del conto dalla porta del suo exchange (campo `network` dell'API invariato).
Spariscono `ExchangeNetwork.of_installation` e `TEST_INSTALLATION`. La pipeline passa `vars.HYPERLIQUID_NETWORK`
dell'environment GitHub (`dev`, `prod`) all'azione `ssh-deploy`, che la scrive nel `.env`; il compose la dà ad `api`
e `worker`. I valori li imposta il proprietario.

Verifica: prova (`tests/unit/adapters/hyperliquid/test_composition.py`, `tests/unit/bootstrap/test_bootstrap.py`).

### Conseguenze

- Ogni installazione dichiara la rete: senza la variabile `api` e `worker` non partono.
- Tutti i conti di un'installazione stanno sulla stessa rete dell'exchange.
