# ADR chiusure-per-protezione-nello-storico — Chiusure per stop loss e take profit nello storico del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.2 (455), Task T3.1.2.3 (475); R1.7.2
- Collegate: ADR ordini-di-protezione-sull-exchange, ADR 0056 (chiusure fuori dalla piattaforma), ADR 0070 (esito
  letto dall'exchange)

## Contesto e problema

Oggi una posizione sparita dall'exchange senza un ordine della piattaforma è «chiusa fuori dalla piattaforma»
(`account_reconciliation._closed_outside`, `RecordOutsideClosingUseCase`). Con gli ordini di protezione la chiusura
per stop loss o take profit è del flusso: R3.1.2 chiede il motivo «stop loss» o «take profit» con l'esito letto
dall'exchange, poi l'annullamento delle protezioni rimaste.

## Fattori decisionali

- Decisioni del proprietario (16/11/2026, piano di E3): stop loss obbligatorio sull'exchange, take profit facoltativo.
- CLAUDE.md: niente ponti tra contesti; il contesto che usa un dato di un altro dichiara la sua porta, realizzata
  nella cartella della tecnologia; la sequenza sta nel caso d'uso.
- ADR 0070: il PnL è quello riportato dall'exchange.

## Opzioni considerate

1. `CloseReason` aggiunge `STOP_LOSS = "stop loss"`, `TAKE_PROFIT = "take profit"` e
   `PROTECTION_MISSING = "stop loss non piazzato"` (chiusura immediata di ADR ordini-di-protezione-sull-exchange). Le
   protezioni piazzate hanno un id cliente della piattaforma: il registro delle esecuzioni (`domain/flows/ledger.py`)
   riconosce le loro esecuzioni come ordini del flusso, con il tipo di protezione. La riconciliazione, per una
   posizione sparita la cui chiusura viene da un'esecuzione di protezione, produce una `ProtectionClosing` (flusso,
   asset, tipo, PnL e commissioni lette dall'esecuzione, istante) invece di una `OutsideClosing`;
   `RecordProtectionClosingUseCase` (`application/flows/record_protection_closing.py`) la registra nello storico come
   fa oggi `RecordOutsideClosingUseCase` (stessa apertura, stesso avviso di chiusura), toglie il piano di uscita in
   vigore e chiede l'annullamento delle protezioni rimaste attraverso una porta di `application/flows/ports.py`
   realizzata nella cartella della tecnologia. Dashboard e API mostrano già il motivo come testo: nessun componente
   nuovo.
2. Lasciare «chiusa fuori dalla piattaforma» e dedurre il motivo dal prezzo: scartato, ambiguo con slippage e
   liquidazioni.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.1.2 sulle chiusure eseguite dall'exchange; unit test della riconciliazione, del
registro e del caso d'uso).

### Conseguenze

- Lo storico distingue protezione, decisione dell'agente e chiusure davvero esterne.
