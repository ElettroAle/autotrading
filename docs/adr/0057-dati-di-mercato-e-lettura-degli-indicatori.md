# ADR 0057 — Dati di mercato dell'exchange e lettura degli indicatori tecnici nel ciclo

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.3.3 (Task T1.3.3.1)

## Contesto

R1.3.3 chiede, per ogni asset del flusso, prezzo corrente, mid price, open interest e funding rate, e su due
timeframe EMA20, MA20, MACD, RSI7, RSI14 e volume (il lungo, di 4 ore, anche EMA50 e MA50), ciascuno come valore
corrente e serie degli ultimi valori (lunghezza da 1 a 50, predefinita 10). Il timeframe breve coincide con
l'intervallo di ciclo del flusso, che va da 1 a 1440 minuti interi (R1.1.1).

I calcoli esistono già nel domain, in Decimal (ADR 0032). Mancano i dati di mercato e il lettore della fonte
dentro il ciclo (`SourceReaderPort`, ADR 0048). Hyperliquid pubblica candele solo a intervalli fissi (1m, 3m,
5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, ...) e i valori correnti di ogni asset in `metaAndAssetCtxs`, entrambi
dall'endpoint pubblico `info`, senza credenziali.

## Decisione

- **Porta** `MarketDataPort` nel contesto `sources`:
  - `candles(asset, timeframe, count, now)`: le ultime candele chiuse;
  - `snapshot(asset)`: valori correnti;
  - `previous_day(asset, now)`: la giornata UTC precedente, per i pivot (ADR 0058).
- **Adapter** `HyperliquidMarketDataAdapter`, accanto a quello dello storico dei prezzi, con l'SDK ufficiale.
  - La candela ancora aperta si scarta: chiusura e volume cambiano fino alla sua chiusura, e un indicatore
    calcolato su di essa cambierebbe a ogni lettura.
  - Prezzo corrente = mark price; mid price = `midPx`; open interest e funding dal contesto dell'asset.
  - Una risposta mancante o in un'altra forma è "fonte non raggiungibile: dati di mercato di Hyperliquid".
- **Timeframe breve** = l'intervallo di candela dell'exchange uguale all'intervallo di ciclo. Per un intervallo
  di ciclo senza candela corrispondente (per esempio 10 o 45 minuti) si usa l'intervallo più fine sotto di esso
  (5m, 30m). Il contesto dichiara sempre il timeframe usato (`breve.timeframe`, `lungo.timeframe`).
- **Storico richiesto**: lunghezza della serie più 100 candele, perché medie a 50 periodi, MACD e RSI abbiano i
  primi valori e l'inizializzazione dell'EMA abbia perso peso. Uno storico più corto rende la fonte assente nel
  ciclo (`InsufficientHistoryError`, ADR 0032).
- **Lettore** `ReadIndicatorsUseCase`, costruito per ogni raccolta con l'intervallo di ciclo della versione della
  configurazione in vigore.
  - Valori: `prezzo`, `mid_price`, `open_interest`, `funding_rate`, poi per ogni timeframe `<breve|lungo>.<indicatore>`
    (valore corrente) e `<breve|lungo>.<indicatore>.serie` (array JSON dal più vecchio al più recente).
  - Il MACD porta anche linea del segnale e istogramma (`MACD_segnale`, `MACD_istogramma`).
  - Ogni numero ha 8 cifre significative, senza esponente.
  - Il dato si riferisce alla chiusura dell'ultima candela breve.
- **Registrazione** in `SourcesFromSources._readers_of`; `CycleServices` porta `market: MarketDataPort`.

## Alternative scartate

- **Aggregare candele più fini per ottenere esattamente l'intervallo di ciclo**: Hyperliquid conserva solo le
  ultime 5000 candele per intervallo; per un intervallo come 1439 minuti servirebbero centinaia di migliaia di
  candele da 1 minuto. La regola sarebbe esatta solo per una parte degli intervalli, e il resto richiederebbe
  comunque un ripiego.
- **Includere la candela aperta**: valori più freschi ma instabili, e un volume parziale confrontato con volumi
  di candele intere.
- **Valori come oggetti annidati nel contesto**: `SourceValue` e il registro dei campioni (ADR 0049) portano testo
  per chiave; la serie in un array JSON resta leggibile dall'agente senza cambiare quel contratto.

## Conseguenze

- Per gli intervalli di ciclo standard (1, 3, 5, 15, 30, 60, 120, 240, 480, 720, 1440 minuti) il timeframe breve
  coincide con l'intervallo. Per gli altri è un'approssimazione dichiarata, da rivedere se il proprietario vuole
  una regola diversa.
- Due chiamate di candele e una dei valori correnti per asset e ciclo, sull'endpoint pubblico.
- Un asset appena quotato, con meno di 110 candele da 4 ore, non ha la fonte indicatori finché lo storico non
  basta.
