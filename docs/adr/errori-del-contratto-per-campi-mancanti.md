# ADR errori-del-contratto-per-campi-mancanti — Errori del contratto per i campi mancanti negli accessi del worker

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 296 (Task 297), Bug 284
- Collegate: ADR accessi-del-worker-come-campi-dichiarati, ADR 0158, ADR 0027

## Contesto e problema

Con il Bug 284 gli accessi del worker portano i campi delle credenziali come mappa. Gli adapter Hyperliquid li
leggevano con `value(nome)` dei tipi del domain, che per un campo mancante solleva l'errore di domain del tipo
(`TradingAccessRequiredError`, `FlowCredentialsMissingError`, `CredentialsRequiredError`); l'opener libsodium
costruiva un accesso anche da un documento con un campo vuoto, lasciando uscire l'invariante del domain. Gli errori che
un adapter solleva sono quelli del contratto della sua porta, dichiarati in `application/<contesto>/errors.py`
(rule layer-application, rilievo di revisione della PR 179).

## Opzioni considerate

### 1. L'adapter legge i campi dalla mappa e solleva l'errore del contratto della porta

- Pro: ogni porta solleva solo i suoi errori; un campo mancante vale come credenziali rifiutate, senza raggiungere
  l'exchange.
- Contro: un piccolo helper per adapter.

### 2. Catturare l'errore di domain nell'adapter e tradurlo

- Pro: nessuna lettura in più.
- Contro: un try/except per un caso che un controllo evita; la regola ammette try solo se indispensabile.

## Esito della decisione

Opzione 1.

- Ordini: un accesso senza un campo dell'exchange è `ExchangeRejectedOrderError` «credenziali del conto incomplete».
- Lettura dello stato, ciclo e verifica: `ExchangeRejectedCredentialsError` con lo stesso motivo, tradotto come
  ogni rifiuto in `FlowCredentialsRefusedError` e `VerificationCredentialsRejectedError`.
- Lettori di attività ed esecuzioni: `FlowCredentialsFieldMissingError`, ora dichiarato nelle porte
  `ActivityReaderPort` ed `ExecutionsReaderPort`.
- Opener libsodium: un documento con un campo vuoto non si apre (`*CredentialsNotOpenedError` del contesto).

Gli errori di domain dei tipi degli accessi restano solo per le loro invarianti.
