# ADR saldo-unified-comprensivo-del-risultato-aperto — Il saldo unified è l'USDC dello stato spot, già comprensivo del risultato aperto

- Stato: proposta (20 novembre 2026)
- Requisiti: Bug 597 (Task 629)
- Sostituisce: la sola regola del saldo in unified account e portfolio margin dell'ADR
  saldo-dalla-modalita-del-conto-hyperliquid (il margine disponibile e il resto restano)
- Collegate: ADR saldo-dalla-modalita-del-conto-hyperliquid, ADR allarme-di-riconciliazione-sul-saldo-del-conto,
  ADR capitale-libero-al-netto-del-valore-dei-flussi; `.claude/rules/tech-hyperliquid.md`
- Verifica: prova

## Contesto e problema

L'ADR saldo-dalla-modalita-del-conto-hyperliquid fissa, per unified account e portfolio margin, saldo = USDC `total`
dello stato spot più il PnL non realizzato delle posizioni perps. La lettura del conto testnet in `unifiedAccount` del
20 novembre 2026 (20 letture in 7 minuti, tre posizioni aperte, nessuna esecuzione, funding o movimento nel periodo)
mostra che `total` contiene già tutto il PnL non realizzato: `total − PnL` resta 1009,238341 a ogni lettura, mentre
`total` segue il prezzo. Lo stesso vale per `hold`, mentre `total − hold` resta costante. Sommare il PnL lo conta due
volte: il saldo mostrato, il capitale libero e il confronto del saldo (R3.3.1) si spostano col prezzo, e la
riconciliazione segnala variazioni non spiegate che non esistono.

## Fattori decisionali

- Decisione del proprietario (20 novembre 2026, in chat): correggere il calcolo del saldo unified sostituendo la
  regola dell'ADR accettata; la modalità resta letta dall'exchange, nessuna impostazione.
- In ogni modalità il saldo è il patrimonio a prezzo corrente, comprensivo del risultato aperto una volta sola: in
  standard lo è già `marginSummary.accountValue`; la riconciliazione toglie il PnL non realizzato dal saldo per
  confrontare la cassa (ADR allarme-di-riconciliazione-sul-saldo-del-conto).

## Decisione

- Unified account e portfolio margin: saldo = USDC `total` dello stato spot, senza aggiungere il PnL non realizzato.
- Il margine disponibile resta `total − hold −` margine delle posizioni isolate, mai sotto zero.
- Standard e modalità non unificate: invariato (`marginSummary.accountValue`, `withdrawable`).
- La correzione è nella traduzione dell'adapter Hyperliquid (`in_account_mode`); riconciliazione, capitale libero e
  dashboard ricevono il saldo corretto senza modifiche.

## Alternative scartate

- Impostazione manuale della modalità nella dashboard: si disallinea se l'utente cambia modalità sull'exchange.
- Togliere il PnL solo nella riconciliazione: il saldo mostrato e il capitale libero resterebbero sbagliati.

## Conseguenze

- Un conto unified mostra come saldo il patrimonio che l'exchange dichiara; il confronto del saldo vede la sola cassa,
  ferma senza movimenti veri.
- Le letture spot e perps restano due richieste distinte: se il prezzo si muove tra le due, il PnL tolto dalla
  riconciliazione non è esattamente quello contenuto in `total`. Nella lettura del 20 novembre è successo in 2 letture
  su 20, con scarti di 0,009 e 0,09 USDC: una variazione non spiegata piccola e rara, sotto la soglia dell'allarme,
  invece di una a ogni ciclo.
