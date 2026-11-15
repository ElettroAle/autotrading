# ADR campi-pubblici-del-conto-conservati-in-chiaro — Campi pubblici del conto conservati in chiaro

- Stato: accettata (15 novembre 2026)
- Requisiti: R0.2.4, R0.2.3, R2.3.1 (Bug 401, Task 402)
- Sostituisce: ADR 0019 (sostituzione delle credenziali con impronta del conto exchange), solo nella parte che non
  conserva il conto in chiaro; l'impronta e il confronto restano
- Collegate: ADR 0007, ADR 0158

## Contesto e problema

La sostituzione delle credenziali chiede tutti i campi che l'exchange dichiara, anche quelli pubblici come l'indirizzo
del conto, che non si può cambiare: le credenziali di un altro conto sono rifiutate (R0.2.4). L'utente si trova a
reinserire un dato che non può modificare, e se lo cambia riceve un rifiuto (Bug 401). L'API non conosce i campi
pubblici registrati: ne conserva solo l'impronta (ADR 0019), e le credenziali cifrate le apre solo il worker
(ADR 0007). Per chiedere solo i segreti qualcuno deve conoscere i campi pubblici registrati e unirli ai segreti nuovi.

## Fattori decisionali

- Nessun segreto in chiaro e solo il worker decifra le credenziali (ADR 0007, R0.2.3).
- Domain, application e dashboard non nominano i dati di un exchange: decide l'adapter quali campi sono segreti
  (ADR 0158).
- L'utente deve poter vedere con quale conto dell'exchange è registrato un conto.

## Opzioni considerate

### 1. Conservare in chiaro i campi che l'adapter dichiara pubblici, accanto all'impronta

- Pro: l'API unisce i campi pubblici conservati ai segreti nuovi, verifica, cifra e salva; nessuna operazione nuova
  del worker.
- Pro: la dashboard mostra i campi pubblici del conto, così un indirizzo sbagliato si vede subito.
- Pro: nessun segreto in chiaro: sono i campi che l'adapter dichiara non segreti; un indirizzo di wallet è pubblico.
- Contro: supera l'ADR 0019 nella parte che non conservava il conto in chiaro.

### 2. Sostituzione nel worker

- Pro: l'impronta resta l'unico dato in chiaro.
- Contro: la chiave nuova viaggia anche tra API e worker; serve un'operazione nuova del worker; la dashboard non può
  mostrare i campi pubblici.

### 3. Solo un messaggio migliore

- Pro: nessun cambiamento ai dati.
- Contro: il modulo continua a chiedere un campo che non si può cambiare: non risolve il Bug.

## Esito della decisione

Opzione 1, approvata dal proprietario.

- `ExchangeAccount` porta, oltre all'impronta, i campi pubblici (`public_fields`), calcolati dai campi che l'adapter
  dichiara non segreti; il confronto tra conti usa solo l'impronta. Il repository li conserva nella colonna nullable
  `accounts.exchange_account_public_fields` (JSON), vuota per i conti registrati prima.
- La registrazione li conserva. La sostituzione di un conto che li conserva accetta solo campi segreti
  (`Credentials.replacing`): un campo pubblico inviato è `PublicCredentialFieldNotReplaceableError` (400) col motivo
  «<etichetta> non si sostituisce: per cambiarlo rimuovi il conto e registrane uno nuovo», costruito dall'etichetta
  che l'adapter dichiara, e non raggiunge l'exchange.
- Un conto senza campi pubblici conservati chiede ancora tutte le credenziali e li conserva alla sostituzione, se le
  credenziali sono dello stesso conto: nessuna nuova registrazione.
- Elenco e dettaglio dei conti espongono `public_fields` per nome; la dashboard li mostra con le etichette che
  l'exchange dichiara (`GET /exchanges`), nella colonna «Conto sull'exchange» e in sola lettura nel modulo di
  sostituzione, che chiede solo i campi non conservati.

## Conseguenze

- Migrazione Alembic `0024` con una colonna nullable; row level security e permessi invariati.
- I segreti restano solo cifrati: mai in risposte, log, errori o repr (R0.2.3).
- Il conto già registrato su dev chiede l'indirizzo un'ultima volta, alla prossima sostituzione.
