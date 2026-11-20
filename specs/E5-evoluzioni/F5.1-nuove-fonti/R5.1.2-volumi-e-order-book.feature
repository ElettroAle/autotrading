# language: it
@R5.1.2
Funzionalità: R5.1.2 Volumi e order book di altri exchange
  Come utente
  Voglio che l'agente veda volumi e ordini anche fuori dall'exchange su cui opera
  Perché capisce se nel mercato prevalgono acquisti o vendite

  Nuova fonte per asset "volumi" con un adapter, Binance (dati pubblici, nessuna configurazione necessaria). Per
  ogni asset del flusso: volume delle ultime 24 ore, rapporto tra acquisti e vendite aggressivi (taker buy/sell)
  sull'intervallo del ciclo, squilibrio dell'order book entro ±1% dal prezzo, cioè la quota del valore in
  acquisto sul totale (RF-12.01). Con più adapter attivi della fonte il contesto riporta ogni exchange e un
  aggregato pesato sui volumi. Un asset non quotato sull'exchange dell'adapter è dichiarato come tale.

  Fuori ambito: altri exchange (Bybit, OKX) e aggregatori a pagamento, aggiungibili come adapter.

  Contesto:
    Dato che il flusso "alfa" ha l'asset "BTC" e la fonte "volumi" con l'adapter "Binance"

  Scenario: Dati di volume e order book nel contesto
    Quando parte il ciclo di "alfa"
    Allora il contesto contiene per "BTC" su Binance volume 24 ore, rapporto taker buy/sell e squilibrio dell'order book entro ±1%

  Scenario: Asset non quotato
    Dato che il flusso "alfa" ha anche un asset non quotato su Binance
    Quando parte il ciclo di "alfa"
    Allora il contesto dice per quell'asset "non quotato su Binance"

  Scenario: Exchange che non risponde
    Dato che Binance non risponde
    Quando parte il ciclo di "alfa"
    Allora la fonte "volumi" è assente nel contesto e il ciclo prosegue
