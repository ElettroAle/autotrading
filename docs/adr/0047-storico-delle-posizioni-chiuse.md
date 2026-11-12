# ADR 0047 — Storico delle posizioni chiuse

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.7.2 (Task T1.7.2.1)

## Contesto

Ogni posizione chiusa di un flusso conserva asset, direzione, leva, prezzi e istanti di apertura e chiusura,
durata, PnL in valore e in percentuale del margine, commissioni, motivo della chiusura e cicli di apertura e
chiusura; lo storico si consulta dalla chiusura più recente (R1.7.2). Per ADR 0026 lo storico è di `flows`.
I fatti che chiudono una posizione arrivano da più requisiti: esecuzione delle decisioni (R1.5.5), stop (R1.1.5),
rimozione del conto (R1.1.8), chiusura manuale (R0.3.2) e attribuzione dall'exchange, che vede le posizioni
sparite senza un ordine della piattaforma, comprese le liquidazioni (R1.6.1).

## Decisione

- **Domain**: `ClosedPosition` (`TenantOwned`) con due `PositionEnd` (prezzo, istante, ciclo che l'ha prodotta o
  nessuno) e `CloseReason` con i cinque motivi di E1. Durata e PnL si calcolano: PnL = margine × leva ×
  (chiusura − apertura) / apertura, col segno della direzione, prima delle commissioni, che restano un valore a
  parte; la percentuale è sul margine. Una posizione che l'exchange non può mostrare (leva sotto 1, margine o
  prezzi non positivi, commissioni negative, istanti senza fuso, chiusura prima dell'apertura) è un difetto.
- **Porta** `ClosedPositionRepositoryPort` (`add`, `of_flow`) legata al tenant, tabella `closed_positions`
  (migrazione 0013) con RLS; al ruolo applicativo solo `SELECT` e `INSERT`: lo storico non si modifica.
- **Consultazione** `ListClosedPositionsUseCase` ordinata dalla chiusura più recente; un flusso di un altro tenant
  risponde "flusso non trovato". Rotta `GET /flows/{id}/closed-positions`, importi come testo senza zeri finali.

## Alternative scartate

- **PnL letto dall'exchange invece che calcolato**: Hyperliquid riporta il PnL realizzato per esecuzione, non per
  posizione; con aperture e chiusure totali (R1.4.4) il calcolo dai prezzi dà lo stesso valore senza una lettura
  in più. Con le esecuzioni parziali di R1.6.1 la scelta si rivede.
- **PnL al netto delle commissioni**: R1.7.2 li riporta come due valori distinti.
- **Storico in `orders`**: `orders` conosce ordini ed esiti del conto, non i flussi né i motivi di chiusura.

## Conseguenze

- Chi chiude una posizione di un flusso (R1.5.5, R1.1.5, R1.1.8, R0.3.2 per i flussi, R1.6.1) la registra con il
  suo motivo attraverso la porta: lo schema "Motivi di chiusura" resta `@wip` fino a quei requisiti.
- La riconciliazione di R1.6.2 (ADR 0045) dichiara `ClosedPositionsPort.add_closed_outside(OutsideClosing)`, senza
  ancora un adapter reale. `OutsideClosing` porta asset, PnL realizzato, commissione e istante di chiusura, ma non
  direzione, leva, margine, prezzo e istante di apertura che `ClosedPosition` richiede: l'adapter, nel ponte di
  integrazione, li ricava dall'ordine di apertura del flusso su quell'asset (contesto `orders`) e salva la
  posizione con motivo "chiusa fuori dalla piattaforma" attraverso `ClosedPositionRepositoryPort`.
