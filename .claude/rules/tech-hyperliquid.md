---
paths:
  - "src/autotrading/adapters/outbound/hyperliquid/**"
  - "tests/unit/adapters/hyperliquid/**"
  - "tests/integration/hyperliquid/**"
---

# Adapter in uscita: Hyperliquid

- Solo l'SDK ufficiale Hyperliquid, importato solo in questa cartella.
- Mainnet e testnet sono due exchange, «Hyperliquid» e «Hyperliquid Testnet», offerti in ogni installazione:
  `HyperliquidTestnetExchangeAdapter` eredita da `HyperliquidExchangeAdapter` e ridefinisce solo rete e indirizzo
  dell'API; gli altri adapter si costruiscono sull'indirizzo della testnet. Le fonti di mercato leggono la rete reale
  (R2.3.11). Mai dedotto dalle credenziali.
- Un solo `HyperliquidSdkAdapter` per processo, creato da `hyperliquid_adapters()` e passato a tutti gli adapter della
  cartella. A ogni uso costruisce un `Info` o un `Exchange` nuovo (la sessione HTTP non si condivide tra thread) con
  `meta` e `spot_meta` già letti: nessuna chiamata di rete nel costruttore. I metadati li legge `_MarketMetadata` e li
  tiene per rete un'ora (`_HyperliquidMetadataSettings`) il decorator `_CachedMarketMetadata`, privati della cartella e
  creati dalla composition; un errore della lettura non si salva (ADR
  metadati-di-mercato-hyperliquid-riusati-dal-client-unico).
- Il prezzo di mercato di una posizione è `positionValue / |szi|` del `clearinghouseState` (R1.4.7).
- Ogni ordine porta il `cloid` assegnato dalla piattaforma.
- Ordini a mercato con lo scostamento massimo ricevuto dal caso d'uso.
- La leva si imposta con il modo di margine ricevuto dal caso d'uso (`is_cross` dell'SDK vero solo per `CROSS`).
- Nessun nuovo tentativo. Timeout di 10 secondi; dopo il timeout l'esito si cerca per `cloid` (R0.3.3).
- L'esito restituito è quello letto dall'exchange (fill reali), non quello richiesto.
- Le eccezioni dell'SDK e di rete si traducono negli errori del contratto della porta
  (es. `ExchangeUnavailableError`, `ExchangeRejectedOrderError` con il motivo dell'exchange).
- Le credenziali non compaiono in log, errori o repr.
- La prova firmata non basta: il ruolo del firmatario (`userRole`) lo lega all'indirizzo del conto, che firma per sé
  o tramite un API wallet approvato proprio per quell'indirizzo (ADR firmatario-autorizzato-per-l-indirizzo-del-conto).
- I test contro testnet hanno il marker `testnet` e non fanno parte della suite di default.
