---
paths:
  - "src/autotrading/adapters/outbound/binance/**"
  - "tests/unit/adapters/binance/**"
  - "tests/integration/sources/test_volumes_live.py"
---

# Adapter in uscita: Binance

- `BinanceVolumesAdapter` realizza `VolumesPort` della fonte `volumi` con gli endpoint pubblici dei dati di mercato di
  Binance (`data-api.binance.vision`, senza chiave), con `httpx` come trasporto (ADR fonte-volumi-con-adapter-binance):
  ticker 24 ore, candele dell'intervallo del ciclo (volume in dollari e volume taker in acquisto), order book.
- Simbolo `<asset>USDT`; un simbolo inesistente (risposta 400 con codice -1121 o -1100) è un asset non quotato,
  `UnlistedAsset`, non un errore.
- Dichiarazione: nome «Binance», nessun campo di configurazione, nessun parametro proprio, `offers_history` vero.
- Ogni altro errore, risposta irraggiungibile o di forma inattesa diventa `SourceUnavailableError`.
- I calcoli (rapporto taker, squilibrio dell'order book, aggregato pesato sui volumi) sono del domain: l'adapter porta
  solo dati grezzi.
- `composition.py` espone `binance_adapters()`, che crea il proprio client `httpx` sull'indirizzo dei dati di mercato;
  `configuration.py` la dataclass privata `_BinanceSettings` con indirizzo e timeout.
- Prova contro l'endpoint vero: `tests/integration/sources/test_volumes_live.py` (marker `integration`, nella
  pipeline a ogni PR).
