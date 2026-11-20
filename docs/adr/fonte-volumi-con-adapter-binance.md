# ADR fonte-volumi-con-adapter-binance — Fonte volumi con l'adapter Binance

- Stato: proposta (19 novembre 2026)
- Requisiti: US 343 R5.1.2, Task 344
- Collegate: ADR fonti-con-adapter-dichiarati, ADR 0105; `.claude/rules/context-sources.md`
- Verifica: prova

## Contesto e problema

R5.1.2 vuole una fonte per asset «volumi» con l'adapter Binance (dati pubblici): volume 24 ore, rapporto taker
buy/sell sull'intervallo del ciclo, squilibrio dell'order book entro ±1% (quota del valore in acquisto sul totale);
con più adapter un aggregato pesato sui volumi; un asset non quotato si dichiara.

## Fattori decisionali

- Decisione del proprietario (backlog E5): Binance pubblico, nessuna configurazione.
- Calcoli e aggregato sono regole del domain; l'adapter porta solo dati grezzi.

## Decisione

- **Domain `sources`**: fonte per asset `volumi`; `VolumeSnapshot(volume_24h_usd, taker_buy, taker_sell, bids, asks)`
  e le regole: rapporto taker = acquisti/vendite aggressivi; squilibrio = valore dei bid entro −1% dal prezzo medio
  diviso il valore di bid e ask entro ±1%; un asset non quotato dà «non quotato su <adapter>». L'aggregato pesato sui
  volumi 24 ore tra gli adapter attivi della stessa fonte è una regola del domain applicata quando si compone il
  contesto del ciclo, presente solo con due o più adapter.
- **Application**: porta `VolumesPort` (`declaration()`, `snapshot(asset, interval_minutes)`) e lettore
  `ReadVolumesUseCase` registrato per (volumi, adapter).
- **Adapter `adapters/outbound/binance/`** (`BinanceVolumesAdapter`): endpoint pubblici dei dati di mercato
  (`data-api.binance.vision`, senza chiave): ticker 24 ore, candele dell'intervallo del ciclo (volume taker in
  acquisto), order book; simbolo `<asset>USDT`; simbolo inesistente = asset non quotato (valore dichiarato, non
  errore). Dichiarazione: nome «Binance», nessun campo, nessun parametro proprio, `offers_history` vero (candele).
  Test di integrazione contro l'endpoint vero come le altre fonti pubbliche (`tests/integration/sources/`).
- `.claude/rules/tech-binance.md` e la cartella `binance/` nell'elenco degli adapter in uscita di `CLAUDE.md`.

## Alternative scartate

- `api.binance.com`: soggetto a blocchi geografici; il dominio dei soli dati di mercato basta.

## Conseguenze

- Bybit e OKX si aggiungono come adapter della stessa fonte e attivano l'aggregato.
