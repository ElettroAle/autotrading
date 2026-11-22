# ADR test-testnet-con-ordini-cancellati — I test che mandano ordini sulla testnet si cancellano

- Stato: proposta (22 novembre 2026)
- Requisiti: Bug 643 (Task 703)
- Collegate: sostituisce la parte «test con ordini sulla testnet in attesa del segreto (marker `testnet_credentials`)» di
  ADR nessun-test-escluso-o-saltato; `.claude/rules/tests.md`, `.claude/rules/ci.md`, `.claude/rules/tech-hyperliquid.md`
- Verifica: prova

## Contesto e problema

`tests/integration/hyperliquid/test_exchange_testnet.py` e `test_protections_testnet.py` mandano ordini sulla testnet e
vogliono le credenziali di un wallet testnet in un file. Il segreto non esiste su GitHub: la pipeline li esclude con il
marker `testnet_credentials` e i loro identificativi sono le sole voci note della regola `NO_EXCLUDED_TESTS`.

## Fattori decisionali

- Decisione del proprietario (22 novembre 2026, in chat): il wallet testnet non si crea; i due test si cancellano.
- ADR nessun-test-escluso-o-saltato: nessun test escluso o saltato; la pipeline esclude solo il marker `pipeline`.

## Decisione

- Si cancellano i due file di test e il loro supporto (`tests/support/testnet_credentials.py` e ciò che serve solo a
  loro), il marker `testnet_credentials` da `pyproject.toml`, la sua esclusione dal comando di pytest della pipeline e le
  loro voci in `tests/architecture/known_violations.py`.
- La regola `NO_EXCLUDED_TESTS` resta com'è: la pipeline esclude solo `pipeline`, senza eccezioni.
- Restano i test di sola lettura sulla testnet e le prove degli ordini con gli adapter finti; le rule che citano i due
  test o il segreto si allineano.

## Alternative scartate

- Wallet testnet nel segreto GitHub: il proprietario non lo crea.
- Ordini su risposte registrate dell'exchange: il proprietario ha scelto la cancellazione.

## Conseguenze

- L'invio di ordini, protezioni e chiusure all'exchange vero non ha più una prova automatica: si vede dal primo uso reale.
