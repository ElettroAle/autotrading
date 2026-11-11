# ADR 0033 — Indici sentiment dagli endpoint pubblici, un adapter per fornitore

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.3.6 (Task T1.3.6.1)

## Contesto

R1.3.6 porta nel ciclo due fonti sentiment di mercato, scelte entrambe dal proprietario perché sono due
indici diversi con lo stesso nome: il Crypto Fear & Greed Index di alternative.me e il CMC Crypto Fear and
Greed Index di CoinMarketCap. Il primo ha un endpoint pubblico senza chiave
(`https://api.alternative.me/fng/?limit=1`). Per il secondo l'ipotesi iniziale era una chiave API della
piattaforma, da creare e montare in sola lettura. La documentazione di CoinMarketCap e una prova diretta
mostrano invece che lo stesso indice è servito senza chiave dal prefisso pubblico
`https://pro-api.coinmarketcap.com/public-api/v3/fear-and-greed/latest`; il percorso `/v3/...` senza
prefisso risponde 401 (codice 1002) se manca la chiave.

Il ciclo (F1.2) che legge le fonti non esiste ancora: gli scenari di R1.3.6 restano `@wip` finché non
arriva.

## Decisione

- **Domain**: `SentimentIndex` (valore intero 0-100, classificazione del fornitore, istante di
  aggiornamento con fuso) in `domain/sources/sentiment_index.py`; una lettura fuori da questi vincoli solleva
  `InvalidSentimentIndexError`.
- **Porta** `SentimentPort.read_index()` in `application/sources/ports.py`: una porta per il ruolo, un adapter
  per fornitore. Il ciclo associa ogni fonte sentiment del catalogo al suo adapter in `bootstrap.py`.
- **Adapter** `HttpxAlternativeMeSentimentAdapter` e `HttpxCoinMarketCapSentimentAdapter` in
  `adapters/outbound/httpx/sentiment.py`, entrambi sugli endpoint pubblici, **senza chiave**. Ogni
  fallimento (rete, stato HTTP diverso da 2xx, corpo non JSON, forma inattesa, valori fuori vincolo) diventa
  `SourceUnavailableError` "fonte non raggiungibile: <nome della fonte>" (503, transitorio), conservando la
  causa: il ciclo tratta la fonte come assente, come chiede lo scenario "Fonte sentiment non raggiungibile".
- **Prova dal vivo** con il marcatore `sources`, esclusa dalla suite ordinaria e dalla pipeline: si esegue a
  mano con `-m sources`, senza alcun segreto.

## Alternative scartate

- **Chiave API di CoinMarketCap montata in sola lettura**: aggiunge un segreto da creare, ruotare e
  proteggere per un dato che il fornitore espone già senza chiave, con lo stesso piano gratuito.
- **Un solo adapter parametrico sui due fornitori**: le due risposte hanno forme diverse (lista di stringhe
  con timestamp Unix contro oggetto con istante ISO); un adapter per fornitore legge ciascuna senza rami.
- **Classificazione calcolata dalla piattaforma**: le due metodologie usano soglie proprie; si riporta la
  classificazione del fornitore così come pubblicata.

## Conseguenze

- Nessun passo manuale del proprietario per il sentiment: nessuna chiave da creare.
- Se CoinMarketCap ritira l'endpoint pubblico, la fonte risulta non raggiungibile a ogni ciclo: la prova dal
  vivo lo rivela, e la decisione si rivede con una nuova ADR.
- Il collegamento al ciclo arriva con F1.2.
