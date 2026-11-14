# ADR 0162 — Nome della rete dichiarato dall'adapter dell'exchange

- Stato: accettata (15 novembre 2026), decisione del proprietario
- Requisiti: R2.3.10 (US 286, Task 287), R2.3.1, R2.2.1
- Collegate: ADR 0155 (rete dalla configurazione dell'adapter), ADR 0157 (rete nell'elenco degli exchange), ADR 0158

## Contesto e problema

L'API diceva solo se la rete di un exchange è di test o reale. Il nome della rete (testnet, mainnet, sandbox...) è
dell'exchange: la dashboard lo scriveva da sé (`test` → `testnet`), cioè conosceva le reti di Hyperliquid. Una
dashboard agnostica deve ricevere anche il nome.

## Opzioni considerate

### 1. L'adapter dichiara il nome della rete, l'API lo espone accanto a `network`

- Pro: la dashboard non nomina alcun exchange né alcuna rete; ogni exchange usa il proprio nome.
- Contro: un metodo in più sulla porta e un campo in più nelle risposte.

### 2. Testo fisso nella dashboard

- Pro: nessun cambiamento all'API.
- Contro: il nome della rete di un exchange finisce nel FE, o si perde.

## Esito della decisione

Opzione 1. `ExchangePort.network_name()` restituisce il nome che l'exchange dà alla rete configurata; Hyperliquid
risponde `testnet` o `mainnet`, gli stessi nomi che `HYPERLIQUID_NETWORK` accetta. Il domain ha `DeclaredNetwork`
(tipo `ExchangeNetwork` e nome); `network_of` lo ricava dalla porta. `GET /exchanges` e `GET /accounts` (elenco e
dettaglio) aggiungono `network_name` accanto a `network`.

Verifica: prova (scenari di R2.3.10, `test_declared_network.py`, `test_exchange.py`, `test_list_supported_exchanges.py`,
`test_list_accounts.py`, `test_exchanges.py`, `test_account_management.py`).
