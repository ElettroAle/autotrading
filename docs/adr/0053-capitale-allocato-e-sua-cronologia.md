# ADR 0053 — Variazione del capitale allocato e sua cronologia

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.1.7 (Task T1.1.7.1)

## Contesto

Il capitale allocato a un flusso si alza o si abbassa in ogni stato tranne archiviato; un aumento non supera il
capitale disponibile del conto, una riduzione non scende sotto il margine impegnato dalle posizioni del flusso; la
variazione vale dal ciclo successivo e resta in una cronologia propria (R1.1.7). La configurazione è già versionata
e ogni ciclo legge la propria versione (ADR 0041).

## Decisione

- **Versione + cronologia**: una variazione produce la versione successiva della configurazione
  (`Flow.with_capital`) e una riga `CapitalChange` (istante, prima, dopo, utente) nella tabella
  `flow_capital_changes` (migrazione 0014, RLS, solo `SELECT` e `INSERT`), nella stessa transazione
  (`FlowRepositoryPort.add_capital_change`).
- **Ammissione**: capitale disponibile = capitale libero del conto (ADR 0031, `free_capital_of`) + il
  capitale attuale del flusso; margine impegnato = somma di dimensione × prezzo di ingresso / leva delle posizioni
  del conto sugli asset del flusso (`FlowPositionsPort.committed_margin`, letta dal `worker`). Errori
  `CapitalAboveAvailableCapitalError` e `CapitalBelowCommittedMarginError` (422) col valore limite.
- Un valore uguale all'attuale non crea versione né riga.
- **API**: `PUT /flows/{id}/allocated-capital`, `GET /flows/{id}/capital-changes`.

## Alternative scartate

- **Cronologia derivata dalle versioni della configurazione**: le versioni cambiano anche per asset e modello;
  filtrare e confrontare versioni adiacenti non dà l'utente né rende la lettura semplice.
- **Margine dal campo `marginUsed` dell'exchange**: è per conto, non per asset del flusso.

## Conseguenze

- Lo scenario "La variazione ha effetto dal ciclo successivo" resta `@wip` finché l'esecutore dei cicli non è
  collegato: la versione nuova c'è, ma nessun ciclo reale la legge ancora.
- Con più flussi sullo stesso asset dello stesso conto il margine impegnato si conta per ognuno: la regola è
  prudente e va rivista se R1.4.4 cambia.
