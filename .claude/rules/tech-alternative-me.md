---
paths:
  - "src/autotrading/adapters/outbound/alternative_me/**"
  - "tests/unit/adapters/test_fear_and_greed_sources.py"
  - "tests/integration/sources/test_sentiment_live.py"
---

# Adapter in uscita: alternative.me

- `AlternativeMeSentimentAdapter` legge il Fear & Greed Index dall'endpoint pubblico di alternative.me
  (ADR 0033), con `httpx` come trasporto. Nessuna chiave.
- Una risposta non raggiungibile o di forma inattesa si traduce nell'errore del contratto della porta di
  `sources`.
- `composition.py` espone `alternative_me_adapters()`, che crea il proprio client `httpx` e l'adapter;
  `configuration.py` la dataclass privata `_AlternativeMeSettings` col timeout.
