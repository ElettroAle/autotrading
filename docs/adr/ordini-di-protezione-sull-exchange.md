# ADR ordini-di-protezione-sull-exchange — Stop loss e take profit come ordini di protezione sull'exchange

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.2 (455), Task T3.1.2.1 (473)
- Collegate: ADR piano-di-uscita-nella-decisione-dell-agente, ADR stop-loss-e-take-profit-predefiniti-del-flusso,
  ADR chiusure-per-protezione-nello-storico, ADR permanenza-decisa-dall-errore-base, ADR
  prezzo-di-mercato-dichiarato-dall-exchange

## Contesto e problema

`ExecuteFlowOrdersUseCase` (`application/orders/execute_flow_orders.py`) invia solo ordini a mercato: tra un ciclo e
l'altro una posizione non ha protezione. R3.1.2 chiede, a ogni apertura, stop loss e (se c'è un obiettivo) take
profit sull'exchange sull'intera posizione, con i livelli dell'agente o i predefiniti del flusso calcolati sul prezzo
d'ingresso reale; uno stop dell'agente oltre il predefinito si riporta al predefinito; uno stop loss rifiutato chiude
subito la posizione; gli ordini rimasti si annullano a ogni chiusura; le posizioni aperte prima ricevono lo stop al
ciclo successivo.

## Fattori decisionali

- Decisioni del proprietario (16/11/2026, piano di E3): stop loss predefinito obbligatorio al 5% dal prezzo
  d'ingresso, anche per i flussi esistenti; take profit facoltativo; l'agente può spostare lo stop mai oltre il
  predefinito e mai toglierlo.
- CLAUDE.md: un adapter = una tecnologia; il caso d'uso orchestra; porte in `application/<contesto>/ports.py`; errori
  dell'exchange tradotti nell'adapter (`raise … from error`); la permanenza la decide l'errore base (ADR
  permanenza-decisa-dall-errore-base).
- SDK Hyperliquid: ordini trigger (`{"trigger": {"triggerPx", "isMarket": true, "tpsl": "sl" | "tp"}}`, `reduce_only`)
  e raggruppamento `positionTpsl` di `bulk_orders`, che lega l'ordine all'intera posizione.

## Opzioni considerate

1. **Domain orders**: `ProtectionKind` (`STOP_LOSS`, `TAKE_PROFIT`), `ProtectionOrder(asset, kind, closing_direction,
   trigger_price, client_order_id)` e `ProtectionRequest(stop, target, default_stop_percent,
   default_take_profit_percent)` portata dal `FlowOpening`. `ProtectionRequest.levels_at(side, entry_price)` dà
   `ProtectionLevels(stop, take_profit, notes)`: stop dell'agente o predefinito (`entry × (1 ∓ percentuale/100)`); uno
   stop dell'agente più lontano dal prezzo d'ingresso del predefinito si riporta al predefinito con la nota
   `"stop <agente> riportato a <predefinito>: oltre lo stop predefinito del <percentuale>%"`; take profit
   dall'obiettivo o dal predefinito, assente se mancano entrambi. Prezzi arrotondati con le regole del `Market`.

   **Porte** in `application/orders/ports.py`: `ProtectionExchangePort` (`place(access, order) -> str` id
   dell'exchange, `cancel(access, asset, order_id)`, `active(access, asset) -> tuple[ActiveProtection, ...]`; rifiuto
   come `ExchangeRejectedOrderError` col messaggio dell'exchange, exchange irraggiungibile come
   `OrderExchangeUnavailableError`) e `ProtectionRepositoryPort` (protezioni piazzate per flusso e asset: tipo,
   prezzo, id dell'exchange, id cliente). Adapter `HyperliquidProtectionExchangeAdapter` in
   `adapters/outbound/hyperliquid/protections.py` (stesso `HyperliquidSdkAdapter` e stessa traduzione degli errori di
   `orders.py`; la dimensione da inviare con `positionTpsl` si verifica con un test di integrazione sulla testnet),
   `SqlAlchemyProtectionRepositoryAdapter` con tabella `flow_protections` (tenant, RLS, migrazione Alembic) e adapter
   finti per i test.

   **Casi d'uso**: dopo un'apertura eseguita `ExecuteFlowOrdersUseCase` chiama `ProtectFlowPositionUseCase`
   (`application/orders/protect_flow_position.py`): calcola i livelli sul prezzo medio dell'esecuzione, piazza lo stop
   loss, poi il take profit, registra le protezioni. Stop loss rifiutato: chiude subito la posizione con un ordine a
   mercato del flusso e la nota `"posizione <asset> chiusa: stop loss non piazzato, <motivo>"`; take profit rifiutato:
   nota `"take profit non piazzato su <asset>, <motivo>"`, la posizione resta col suo stop. `CancelProtectionsUseCase`
   annulla le protezioni rimaste di flusso e asset (sull'exchange e nel repository) dopo ogni chiusura: agente,
   comando manuale, stop del flusso, rimozione del conto, chiusura fuori piattaforma o per protezione.
   `ProtectOpenPositionsUseCase`, all'inizio del passo «esecuzione degli ordini» di ogni ciclo, piazza lo stop
   predefinito sul prezzo d'ingresso per ogni posizione del flusso senza stop loss attivo sull'exchange. Le note vanno
   nel documento del passo «esecuzione degli ordini».
2. Stop sorvegliato dal worker a ogni ciclo: scartato, la posizione resta scoperta tra i cicli e a piattaforma ferma.
3. Stop e take profit nello stesso invio dell'apertura (`normalTpsl`): scartato, i predefiniti si calcolano sul prezzo
   d'ingresso reale, noto solo dopo l'esecuzione.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.1.2 con adapter finti; unit test di `ProtectionRequest` e dei casi d'uso; test di
integrazione dell'adapter Hyperliquid sulla testnet e del repository su PostgreSQL).

### Conseguenze

- Ogni posizione di un flusso ha sempre uno stop loss sull'exchange, anche a piattaforma ferma.
- R3.1.3 sostituisce le protezioni con le stesse porte.
