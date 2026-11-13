---
paths:
  - "src/autotrading/adapters/outbound/coinmarketcap/**"
  - "tests/unit/adapters/test_fear_and_greed_sources.py"
  - "tests/integration/sources/test_sentiment_live.py"
---

# Adapter in uscita: CoinMarketCap

- `CoinMarketCapSentimentAdapter` legge il Fear and Greed Index dall'endpoint pubblico di CoinMarketCap
  (ADR 0033), con `httpx` come trasporto.
- Una risposta non raggiungibile o di forma inattesa si traduce nell'errore del contratto della porta di
  `sources`.
- `composition.py` espone `coinmarketcap_adapters()`, che crea il proprio client `httpx` e l'adapter;
  `configuration.py` la dataclass privata `_CoinMarketCapSettings` col timeout.
