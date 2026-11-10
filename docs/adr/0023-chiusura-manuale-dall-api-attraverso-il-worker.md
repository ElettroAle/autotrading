# ADR 0023 — Chiusura manuale delle posizioni dall'API attraverso il worker

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.3.2

## Contesto

R0.3.2 chiede che un utente chiuda in qualunque momento, per intero, una posizione aperta su un suo
conto. L'esito riporta prezzo medio di chiusura, profitto o perdita realizzati e commissione. La
chiusura si registra con il motivo "comando manuale" e l'utente. Una posizione inesistente fallisce
senza inviare ordini. L'utente non può aprire posizioni a mano.

Gli ordini usano le credenziali salvate, che apre solo il `worker` (ADR 0021). Il contesto `orders`
(ADR 0022) ha la porta `TradingAccessPort` ancora senza collegamento, e lo scostamento massimo arriva
dal costruttore del caso d'uso.

## Decisione

- **Due casi d'uso, come per lo stato del conto (ADR 0021).**
  - `ClosePositionUseCase` (API) riceve conto, coin e utente dell'identità. Chiede la chiusura alla
    porta `PositionClosingPort` e restituisce un `OrderOutcome`: identificativo, stato, dimensione
    eseguita, prezzo medio, commissione, risultato realizzato, istante, motivo e messaggio di un rifiuto.
    L'appartenenza del conto al tenant la verifica il `worker` sotto RLS: un conto di un altro tenant
    risponde "non trovato" prima di aprire le credenziali (R0.1.3).
  - `CloseExchangePositionUseCase` (`worker`):
    1. accesso al conto;
    2. scelta dell'exchange;
    3. lettura della posizione sull'asset: se non c'è, `NoOpenPositionError` "nessuna posizione aperta su
       ETH" e nessun ordine;
    4. ordine `reduce_only` per l'intera dimensione, con la leva della posizione;
    5. invio con le stesse regole dell'apertura (un solo invio, ricerca per `cloid`);
    6. registrazione con origine "comando manuale" e utente.
- **Domain**: `HeldPosition` (coin, direzione, dimensione, leva) con `closing_order(slippage)`, che
  restituisce l'ordine opposto `reduce_only` per l'intera dimensione. `ExchangePort.position(access, coin)`
  la legge; su Hyperliquid da `user_state.assetPositions`.
- **HTTP interno**: il `worker` espone `POST /tenants/{tenant}/accounts/{conto}/positions/{coin}/close`
  con l'utente nel corpo, protetto dallo stesso token (ADR 0021). `HttpxPositionClosingAdapter` riporta le
  risposte agli errori della porta di `orders`:
  - 404: "non trovato";
  - 409: nessuna posizione aperta;
  - 503 con il motivo "exchange non raggiungibile": exchange non raggiungibile;
  - qualunque altra risposta: `OrderWorkerUnavailableError`.
  Il `worker` raccoglie i suoi casi d'uso in `WorkerUseCases`, come l'API fa con `TenantUseCases`.
- **API**: `POST /accounts/{conto}/positions/{coin}/close` restituisce l'esito, anche quando l'ordine è
  rifiutato o ha esito sconosciuto: l'esito è il risultato della richiesta (R0.3.3).
  `POST /accounts/{conto}/positions` risponde sempre 403 "apertura manuale non consentita", senza
  chiamare nulla. Una rotta che risponde sempre di no è più chiara di un 405, che direbbe solo che il
  metodo non esiste.
- **Ponte tra i contesti**: `TradingAccessFromAccounts` in `bootstrap.py` implementa `TradingAccessPort`
  con il repository dei conti del tenant e l'opener del `worker`. Un conto inesistente diventa
  `OrderAccountNotFoundError`.
- **Scostamento configurato**: `ORDER_MAX_SLIPPAGE_PERCENT` nella configurazione del `worker`.
  - Assente o vuoto: 5%.
  - Non numerico: il `worker` non parte, con `InvalidConfigurationError`.
  - Fuori da (0, 100): il `worker` non parte, con `InvalidSlippageError`.
- **Rilascio**: nessun servizio nuovo; la variabile non si imposta in dev, che usa il 5%.

## Alternative scartate

- **API che verifica il conto prima di chiamare il `worker`**: importerebbe `accounts` dentro `orders`, o
  richiederebbe un'altra porta per una verifica che il `worker` fa comunque sotto RLS.
- **Esito di un rifiuto come errore HTTP**: R0.3.3 lo vuole riportato e registrato come esito, non come
  guasto della richiesta.
- **Chiusura con `market_close` senza dimensione**: lascerebbe all'SDK la lettura della posizione. La
  piattaforma deve rispondere "nessuna posizione aperta" prima di inviare qualunque ordine.
- **Ponte in un adapter dedicato**: non è una tecnologia; il punto che conosce entrambi i contesti è
  `bootstrap`.

## Conseguenze

- Una chiusura costa tre chiamate all'exchange: stato del conto, ordine, fill.
- La posizione può cambiare tra lettura e invio: l'ordine `reduce_only` non può comunque aprire
  esposizione opposta.
