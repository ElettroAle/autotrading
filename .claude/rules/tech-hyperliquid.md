---
paths:
  - "src/autotrading/adapters/outbound/hyperliquid/**"
  - "tests/unit/adapters/hyperliquid/**"
  - "tests/integration/hyperliquid/**"
---

# Adapter in uscita: Hyperliquid

- Solo l'SDK ufficiale Hyperliquid, importato solo in questa cartella.
- Mainnet o testnet si sceglie per configurazione dell'installazione, mai dedotto dalle credenziali.
- Ogni ordine porta il `cloid` assegnato dalla piattaforma.
- Ordini a mercato con lo scostamento massimo ricevuto dal caso d'uso.
- La leva si imposta con il modo di margine ricevuto dal caso d'uso (`is_cross` dell'SDK vero solo per `CROSS`).
- Nessun nuovo tentativo. Timeout di 10 secondi; dopo il timeout l'esito si cerca per `cloid` (R0.3.3).
- L'esito restituito è quello letto dall'exchange (fill reali), non quello richiesto.
- Le eccezioni dell'SDK e di rete si traducono negli errori del contratto della porta
  (es. `ExchangeUnavailableError`, `ExchangeRejectedOrderError` con il motivo dell'exchange).
- Le credenziali non compaiono in log, errori o repr.
- I test contro testnet hanno il marker `testnet` e non fanno parte della suite di default.
