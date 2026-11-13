# ADR 0078 — Quota e limiti percentuali del rischio sui soldi del flusso

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.5.1, R1.4.3, R1.4.4, R1.6.1
- Collegate: ADR 0040 (controllo del rischio), di cui cambia la base della quota e dei limiti; ADR 0063 (totali
  del registro), da cui vengono PnL realizzato, commissioni e funding; ADR 0065 (liquidità impegnata per apertura)

## Contesto

Il controllo del rischio (ADR 0040) dimensionava il margine di un'apertura come quota del **capitale allocato** e
calcolava i limiti di esposizione sul margine e sul valore come percentuale dello stesso capitale. Dopo le perdite
un flusso con 1000 USDC allocati e 400 USDC persi in posizioni chiuse apriva con quota 0,4 ancora 400 USDC di
margine, il 67% dei 600 USDC che ha davvero; dopo i guadagni restava fermo alla dimensione iniziale. Il limite
percentuale perdeva il suo significato proprio quando serve. Il proprietario ha deciso che quote e limiti si
misurano sui soldi veri del flusso.

## Decisione

- **Soldi del flusso** (`FlowState.funds`, dominio `flows`): capitale allocato più PnL realizzato, meno
  commissioni, più funding, dai totali del registro (ADR 0063). La liquidità disponibile diventa i soldi meno il
  margine delle posizioni aperte, con lo stesso valore di prima.
- `RiskState` porta `funds` al posto di `allocated_capital`: `RiskCheck` usa i soldi per il margine
  (`quota × soldi`) e per i due limiti di esposizione (`soldi × percentuale`, con la leva per il limite sul margine).
  Il dominio non conosce né exchange né numeri dell'exchange: i limiti dell'exchange arrivano dalla porta
  `ExchangeLimitsPort` come prima.
- `CycleFlow.risk_state()` (bootstrap) costruisce lo stato del rischio dallo stato attribuito del flusso: i soldi
  da `FlowState.funds`, la liquidità limitata al margine libero del conto (ADR 0062).
- Il contesto dell'agente riceve anche `soldi_del_flusso` e l'istruzione dice che la quota è una frazione dei
  soldi del flusso, così l'agente ragiona sulla stessa base del controllo.

## Alternative scartate

- **Valore complessivo** (con il PnL non realizzato): la dimensione delle aperture oscillerebbe col prezzo delle
  posizioni ancora aperte, e una posizione in guadagno farebbe crescere le altre prima di aver incassato nulla.
- **Capitale allocato** (la scelta precedente): ignora le perdite, il caso in cui il limite serve di più.
- **Calcolo dei soldi nel bootstrap**: metterebbe una regola di business nella composition root; la formula sta
  nel dominio accanto alla liquidità che ne deriva.

## Conseguenze

- Dopo 400 USDC persi su 1000 allocati, quota 0,4 impegna 240 USDC; dopo 200 guadagnati, 480. Con esposizione
  massima del margine al 50% e 400 persi, il limite è 300 USDC.
- Con soldi a zero o negativi l'apertura si blocca per liquidità insufficiente o per importo sotto il minimo
  dell'exchange, con i motivi esistenti.
- Senza perdite, guadagni, commissioni o funding i numeri restano quelli di prima: gli scenari di R1.5.2-R1.5.4
  non cambiano.
- Il rendimento resta misurato sul capitale allocato (R1.1.7).
