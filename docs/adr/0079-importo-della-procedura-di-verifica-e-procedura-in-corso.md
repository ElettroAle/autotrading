# ADR 0079 — Importo della procedura di verifica e procedura in corso condivisa tra API e worker

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.4.1
- Collegate: ADR 0024 (procedura di verifica nel worker), ADR 0075 (procedura fuori dai flussi), ADR 0042 (lock del
  flusso durante il ciclo), ADR 0077 (formato italiano degli importi)

## Contesto

La procedura di verifica apriva sempre BTC long con leva 2 per 12 USDC e chiedeva almeno 12 USDC di margine. Il
proprietario ha approvato due criteri nuovi su R0.4.1:

- **Importo libero (B2)**: l'utente sceglie il valore. Se non lo indica vale il minimo dell'exchange del conto. Il
  minimo e le regole dell'ordine vengono dall'exchange e cambiano da un exchange all'altro: il domain non li cabla.
- **Flussi bloccati durante la procedura (B)**: mentre la procedura è in corso su un asset di un conto, un flusso
  del conto su quell'asset non si avvia e non riprende. L'ADR 0075 rifiuta la procedura su un asset di un flusso
  attivo o in pausa. Il caso inverso restava aperto: la procedura gira nel worker, il comando del flusso arriva
  all'API, e i due processi non condividono memoria.

## Decisione

- **Valore dell'apertura nel domain, minimo dall'exchange**:
  - `procedure.py` dichiara solo ciò che la procedura è: `PROCEDURE_COIN = "BTC"`, `PROCEDURE_SIDE = "long"`,
    `PROCEDURE_LEVERAGE = 2`.
  - `procedure_opening(chosen, exchange_minimum, currency)` costruisce l'`Opening` del valore scelto, oppure del minimo
    se l'utente non sceglie. Un importo sotto il minimo solleva `AmountBelowMinimumError` (409, "importo sotto il
    minimo dell'exchange: 10 USDC"). Un importo non positivo solleva `VerificationAmountNotPositiveError` (422).
  - Il margine richiesto è `Opening.required_margin`, cioè valore diviso leva. `InsufficientMarginError` dice
    "margine disponibile insufficiente: servono 10 USDC". Importi e valuta seguono il formato dell'ADR 0077 e la
    valuta letta dal conto.
- **Porta per il minimo**:
  - `OrderExecutionPort.minimum_value(account_id, coin)` legge il valore minimo che l'exchange del conto accetta
    sull'asset.
  - Il ponte `OrderExecutionFromOrders` lo prende da `ReadMarketUseCase` del contesto `orders`. È lo stesso `Market`
    che `OpenPositionUseCase` usa per dimensionare l'ordine, quindi la procedura e l'invio leggono una sola regola.
  - Il valore 10 USDC esiste solo nell'adapter Hyperliquid.
  - Ordine dei controlli, tutti prima di ogni ordine: procedura già in corso, flusso sull'asset, lettura del conto,
    minimo, posizione aperta, margine.
- **Procedura in corso come advisory lock di PostgreSQL**:
  - `VerificationRunRepositoryPort.running(account_id, coin)` è un context manager che segna la procedura in corso
    per tutta la sua durata. Se una procedura è già in corso sullo stesso conto e asset solleva
    `VerificationInProgressError` (409, "procedura di verifica già in corso su BTC").
  - Nel contesto `flows`, `RunningVerificationsPort.kept_free(account_id, assets)` tiene gli asset liberi da procedure
    mentre `ChangeFlowStatusUseCase` registra lo stato attivo, cioè per avvia e riprendi. Se una procedura è in
    corso solleva `AssetUnderVerificationError` (409, "procedura di verifica in corso su BTC"). Pausa e arresto non
    passano dalla porta.
  - Entrambe le porte usano `verification_locks` in `adapters/outbound/sqlalchemy/verification_locks.py`: un
    `pg_try_advisory_lock(int, int)` per asset. La chiave sono i primi otto byte di SHA-256 di `account:asset`. Il
    lock vive sulla sessione di una connessione tenuta per tutto il contesto, fuori da transazioni, e si rilascia in
    `finally` o con la connessione se il processo muore.
  - La forma a due chiavi da 32 bit ha uno spazio separato dalle chiavi da 64 bit dei flussi in ciclo (ADR 0042).
  - Gli adapter provano il lock senza mai aspettare: chi lo trova occupato rifiuta subito.
- **Corsa tra le due parti**:
  - La procedura controlla i flussi del conto dopo aver preso il lock.
  - Il comando del flusso tiene i lock dei suoi asset finché il nuovo stato è scritto.
  - In qualunque ordine arrivino, una delle due parti vede l'altra: o la procedura trova il flusso attivo (ADR 0075),
    o il flusso trova il lock della procedura.
- **API**:
  - `POST /accounts/{id}/verifications` accetta un corpo facoltativo `{"amount": "20"}`, con l'importo maggiore di
    zero validato dallo schema (422).
  - L'API passa l'importo al worker come testo, perché un JSON numerico perderebbe precisione.
  - Senza corpo la procedura apre il minimo.

## Alternative scartate

- **Riga "procedura in corso" in una tabella**: un worker che muore a metà lascia la riga e blocca il conto finché
  qualcuno la pulisce. Servirebbero una scadenza e una pulizia, mentre il lock di sessione sparisce con la
  connessione.
- **Lock in memoria nel worker**: l'API, che riceve avvia e riprendi, non lo vede.
- **Chiedere al worker via HTTP se una procedura è in corso**: aggiunge una chiamata al comando del flusso e lascia
  comunque aperta la corsa tra la domanda e la scrittura dello stato.
- **Lock da 64 bit derivato da conto e asset**: condividerebbe lo spazio delle chiavi con i flussi in ciclo, con
  una collisione possibile, anche se improbabile, con il lock di un flusso.
- **Minimo dalla porta dei limiti dei flussi (`ExchangeLimitsPort`)**: è del contesto `flows`. La verifica invia i
  suoi ordini attraverso `orders`, e il minimo che conta è quello con cui `orders` dimensiona l'ordine.
- **Attesa del lock invece del rifiuto**: avvia o riprendi resterebbero appesi per la durata della procedura, circa
  dieci chiamate all'exchange; il rifiuto dice subito all'utente cosa succede.

## Conseguenze

- Su un exchange nuovo il minimo arriva dal suo adapter di `orders`, senza toccare domain e application.
- Una procedura lanciata nell'istante in cui un flusso dello stesso conto e asset cambia stato viene rifiutata come
  "già in corso". È raro e la ripetizione funziona.
- Ogni avvio e ripresa di un flusso tiene per un momento una connessione in più al database.
- Una seconda procedura sullo stesso conto e asset, anche lanciata da un'altra scheda, viene rifiutata invece di
  mescolare gli ordini sulla stessa posizione.
