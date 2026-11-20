---
paths:
  - "src/autotrading/adapters/outbound/lunarcrush/**"
  - "tests/unit/adapters/lunarcrush/**"
  - "tests/integration/sources/test_lunarcrush_recorded.py"
  - "tests/integration/sources/recorded/lunarcrush/**"
---

# Adapter in uscita: LunarCrush

- `LunarCrushSocialAdapter` realizza `SocialPort` della fonte `social` con l'API v4 di LunarCrush, con `httpx` come
  trasporto (ADR fonte-social-con-adapter-lunarcrush): le ore dell'ultimo giorno della moneta
  (`GET /public/coins/<simbolo>/time-series/v2`, `bucket=hour`, `interval=1d`) per sentiment, menzioni (post creati) e
  interazioni, e i messaggi più rilevanti del topic della moneta (`GET /public/topic/<topic>/posts/v1`), ordinati per
  interazioni delle ultime 24 ore.
- Dichiarazione: nome «LunarCrush», campo segreto «chiave API», parametro proprio `numero_messaggi` (predefinito 5, da 1
  a 20), `offers_history` falso. La chiave è del tenant (R4.1.2) e viaggia solo nell'intestazione
  `Authorization: Bearer` della sua richiesta.
- La somma delle ore e il sentiment pesato sulle interazioni sono del domain (`SocialSnapshot.of_hours`), come lo scarto
  dei messaggi oltre il numero richiesto; l'adapter porta i dati grezzi e lascia fuori i messaggi senza testo.
- 401 e 403 diventano `SourceCredentialsRejectedError`, ogni altro errore, risposta irraggiungibile o di forma inattesa
  `SourceUnavailableError`; la permanenza la decide l'errore base dal codice conservato nella causa.
- `composition.py` espone `lunarcrush_adapters()`, che crea il proprio client `httpx` sull'indirizzo dell'API;
  `configuration.py` la dataclass privata `_LunarCrushSettings` con indirizzo e timeout.
- Prove su risposte HTTP registrate dalla documentazione ufficiale, senza chiave (ADR
  risposte-http-registrate-per-i-fornitori-a-chiave): `tests/integration/sources/test_lunarcrush_recorded.py`.
