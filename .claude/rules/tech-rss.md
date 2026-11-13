---
paths:
  - "src/autotrading/adapters/outbound/rss/**"
  - "tests/unit/adapters/rss/**"
  - "tests/integration/sources/test_news_live.py"
---

# Adapter in uscita: feed RSS

- `RssNewsAdapter` legge le notizie dai feed RSS pubblici dichiarati nel modulo (ADR 0034), con
  `httpx` come trasporto e il parser XML della libreria standard.
- Un feed non raggiungibile o malformato si traduce nell'errore del contratto della porta di `sources`.
- Le notizie restituite sono value object del dominio; titoli e link non si interpretano qui.
- `composition.py` espone `rss_adapters()`, che crea il proprio client `httpx` e l'adapter;
  `configuration.py` la dataclass privata `_RssSettings` col timeout.
