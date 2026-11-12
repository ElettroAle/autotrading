# ADR 0066 — Arrotondamento della quantità che non scende sotto il minimo dell'exchange

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.5.4, R1.5.5, Bug 159 (B1.5.2)

## Contesto

Il controllo del rischio approva un'apertura, o la porta, al valore minimo dell'exchange (10 USDC su
Hyperliquid). La quantità si ricava poi dal prezzo medio e si arrotonda per difetto al passo dell'asset
(`Market.size_for`): 10 USDC su BTC a 60123 con 5 decimali danno 0,00016, cioè 9,62 USDC, sotto il minimo, e
l'exchange rifiuta l'ordine che il rischio aveva approvato.

## Opzioni considerate

### 1. Il mercato conosce il minimo; per difetto, salvo quando scenderebbe sotto il minimo: allora per eccesso

- Pro: la regola sta dove si arrotonda (domain di `orders`); vale per ogni apertura, del flusso o manuale
  (R0.3.1); un valore sotto il minimo non viene mai alzato, e l'aumento è al più di un passo.
- Contro: `Market` riceve un campo in più, dato dall'adapter dell'exchange.

### 2. Il rischio alza il valore di un margine di sicurezza sopra il minimo

- Pro: nessun cambio in `orders`.
- Contro: il margine giusto dipende da prezzo e passo dell'asset, che il rischio non conosce; si impegnerebbe
  più del necessario.

### 3. L'esecuzione riprova con un passo in più dopo il rifiuto

- Pro: nessuna conoscenza del minimo.
- Contro: un rifiuto in più per ogni caso e due ordini registrati per una decisione.

## Esito della decisione

Scelta: **opzione 1**. `Market.min_order_value` (Hyperliquid: `MIN_ORDER_VALUE`, ora nel modulo comune
dell'adapter e usato sia dai limiti del rischio sia dal mercato degli ordini). `size_for` arrotonda per difetto;
se il valore chiesto è almeno il minimo e la quantità arrotondata varrebbe meno del minimo, arrotonda per eccesso
al passo successivo.

### Conseguenze

- Un ordine al minimo può valere fino a un passo in più del valore approvato (0,00017 BTC = 10,22 USDC per 10).
- Un valore chiesto sotto il minimo resta arrotondato per difetto e l'exchange lo rifiuta, come prima.
