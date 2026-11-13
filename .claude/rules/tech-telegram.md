---
paths:
  - "src/autotrading/adapters/outbound/telegram/**"
  - "tests/unit/adapters/telegram/**"
---

# Adapter in uscita: Telegram

- Bot API di Telegram (`https://api.telegram.org/bot<token>/...`) raggiunta con `httpx`, libreria di
  trasporto condivisa; nessuna altra cartella chiama Telegram.
- Solo il `worker` tiene il token del bot dell'installazione, letto da file montato in sola lettura
  (ADR 0070). **Mai variabili d'ambiente.** L'`api` chiede al worker, attraverso `adapters/outbound/worker/`,
  ciò che serve del bot (notifiche, link di avvio).
- `TelegramMessengerAdapter`, `TelegramInboxAdapter`, `TelegramBotIdentityAdapter` realizzano le porte di
  `application/notifications/ports.py`; il link di avvio `https://t.me/<bot>?start=<codice>` si
  compone solo qui.
- `composition.py` espone `telegram_adapters(token)`, che crea client e adapter; `configuration.py` la
  dataclass privata `_TelegramSettings`. Senza token il canale è spento: `TelegramDisabledMessengerAdapter`
  fa fallire ogni messaggio, che si registra senza fermare i flussi.
- Errori HTTP o risposte inattese si traducono negli errori del contratto della porta o si registrano
  senza fermare il chiamante (R1.8.2). Il token non compare in log, errori o repr.
