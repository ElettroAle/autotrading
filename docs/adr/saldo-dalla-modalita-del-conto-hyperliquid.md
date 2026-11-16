# ADR saldo-dalla-modalita-del-conto-hyperliquid — Saldo e margine dalla modalità del conto Hyperliquid

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 392 (Task 393), R0.2.1, R1.1.7, R1.6.1
- Collegate: ADR 0067, ADR 0095, ADR 0158

## Contesto e problema

Hyperliquid ha più modalità di conto (Account abstraction modes): standard (perps e spot separati), unified account
(un saldo per asset, comune a spot e perps; raccomandata e predefinita per i conti nuovi) e portfolio margin. Sotto
unified account e portfolio margin la documentazione dice che lo stato spot (`spotClearinghouseState`) è la fonte di
verità del saldo, e che lo stato perps non è significativo per il saldo. L'adapter legge solo lo stato perps
(`clearinghouseState`): un conto unified con 999 USDC risulta a 0, e nessun flusso riceve capitale.

## Opzioni considerate

### 1. L'adapter legge la modalità del conto e calcola saldo e margine dalla fonte giusta

- Pro: vale per ogni modalità; la modalità la dichiara l'exchange (`userAbstraction`), nessuna configurazione.
- Pro: posizioni, leva e margine delle posizioni restano dallo stato perps, che le descrive in ogni modalità.
- Contro: due letture in più per ogni stato del conto.

### 2. Sommare sempre saldo perps e saldo spot in USDC

- Pro: una regola sola.
- Contro: in standard il saldo spot non è collaterale dei perps: il capitale libero includerebbe soldi che i flussi
  non possono usare.

### 3. Chiedere all'utente di passare il conto in modalità standard

- Pro: nessun codice.
- Contro: la piattaforma non legge correttamente la modalità raccomandata da Hyperliquid.

## Esito della decisione

Opzione 1.

- Standard e modalità non unificate: saldo = `marginSummary.accountValue`, margine disponibile = `withdrawable`
  (come oggi).
- Unified account e portfolio margin: saldo = USDC `total` dello stato spot più il PnL non realizzato delle posizioni
  perps; margine disponibile = USDC `total` meno `hold` (ciò che gli ordini impegnano) meno il margine delle posizioni
  isolate, mai sotto zero.
- Posizioni, leva, prezzi e `marginUsed` restano dallo stato perps (ADR 0067). Gli ordini a mercato con margine
  isolato funzionano in unified account: il margine isolato di una posizione si prende dal saldo USDC unificato
  (documentazione: «available = spot total − isolated margin» nel rapporto del conto unified).
- La lettura vale per registrazione, verifica, ciclo e capitale libero, che passano tutti da `read_state`, e per la
  lettura dello stato prima degli ordini; vale anche per l'attività del conto letta dal worker per la dashboard.

### Conseguenze

- Ogni lettura dello stato del conto fa due richieste in più all'exchange (`userAbstraction` e
  `spotClearinghouseState`), entro gli stessi limiti di frequenza delle letture esistenti.
- Un conto unified mostra come saldo l'USDC che detiene, e i flussi ricevono capitale da quello.
- Nei conti unified il margine disponibile toglie anche il margine delle posizioni isolate, che l'exchange prende dallo
  stesso saldo USDC.
- Un errore di una delle due letture, o una risposta di forma inattesa, rende l'exchange non disponibile: mai un saldo
  inventato.
- Una modalità nuova che l'exchange introducesse si legge come quelle non unificate finché non la si aggiunge.
