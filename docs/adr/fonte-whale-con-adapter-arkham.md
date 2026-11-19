# ADR fonte-whale-con-adapter-arkham — Fonte whale con l'adapter Arkham

- Stato: proposta (19 novembre 2026)
- Requisiti: US 341 R5.1.1, Task 342
- Collegate: ADR fonti-con-adapter-dichiarati, ADR credenziali-degli-adapter-delle-fonti, ADR
  risposte-http-registrate-per-i-fornitori-a-chiave, ADR 0105; `.claude/rules/context-sources.md`
- Verifica: prova

## Contesto e problema

R5.1.1 vuole una fonte di mercato «whale» con l'adapter Arkham: i trasferimenti dell'ultimo intervallo del flusso
sopra una soglia di controvalore (parametro dell'adapter, predefinito 1.000.000 USD), con data e ora, asset,
quantità, controvalore e descrizione di origine e destinazione quando nota; senza trasferimenti il contesto lo dice.

## Fattori decisionali

- Decisione del proprietario (backlog E5): Arkham, chiave gratuita in Impostazioni › Chiavi.
- Una tecnologia per cartella; il domain non nomina fornitori; nuove fonti come adapter (ADR fonti-con-adapter-dichiarati).

## Decisione

- **Domain `sources`**: nuova fonte di mercato `whale` nel catalogo; value object `WhaleTransfer(at, asset, quantity,
  usd_value, origin | None, destination | None)`; la lettura senza trasferimenti dà il valore «nessun grande
  trasferimento nell'ultimo intervallo» (la fonte non è assente).
- **Application**: porta `WhaleTransfersPort` (`declaration()`, `transfers(since, until, minimum_usd, credentials)`)
  e lettore `ReadWhaleTransfersUseCase`, registrato per (whale, adapter) nella costruzione comune dei lettori;
  l'intervallo è l'intervallo di ciclo del flusso, già passato agli indicatori.
- **Adapter `adapters/outbound/arkham/`** (`ArkhamWhaleTransfersAdapter`, `configuration.py` con URL e timeout,
  `composition.py`): API Intel di Arkham, endpoint dei trasferimenti filtrato per istante e controvalore minimo,
  chiave nell'intestazione indicata dalla documentazione; descrizioni da entità ed etichette quando presenti.
  Dichiarazione: nome «Arkham», campo segreto «chiave API», parametro proprio `soglia_usd` (predefinito 1.000.000,
  da 100.000 a 1.000.000.000), `offers_history` vero (filtro per istante). Errori HTTP tradotti nell'errore tipizzato
  della porta (401/403 permanenti per l'errore base).
- `.claude/rules/tech-arkham.md` e la cartella `arkham/` nell'elenco degli adapter in uscita di `CLAUDE.md` (struttura,
  non processo).

## Alternative scartate

- Whale Alert: fuori ambito per decisione del proprietario.

## Conseguenze

- L'adapter non è attivabile finché il tenant non inserisce la chiave (R4.1.2).
