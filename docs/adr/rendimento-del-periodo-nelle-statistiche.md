# ADR rendimento-del-periodo-nelle-statistiche — Le statistiche del flusso mostrano il rendimento del periodo

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 689 (Task 695, 696); R2.2.6, R3.4.3
- Collegate: ADR del rendimento corretto dopo incassi e variazioni (R3.4.3)
- Verifica: prova

## Contesto e problema

R3.4.3: «lo stesso rendimento vale ovunque compaia: stato e riepilogo, classifica, statistiche (R2.2.6)». `FlowStatistics`
(`domain/flows/flow_statistics.py`) e il pannello delle statistiche non hanno un rendimento.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): nelle statistiche, che hanno un periodo, il rendimento del
  periodo: composto dei sotto-periodi dentro il periodo scelto con la regola di R3.4.3; con «Dall'inizio» coincide con
  quello del riepilogo.

## Decisione

- Il calcolo del rendimento composto di R3.4.3 già usato dal riepilogo si applica alla finestra del periodo: valore
  all'inizio del periodo (o all'avvio, se dopo) e a ogni variazione di capitale nella finestra, valore alla fine.
  `FlowStatistics` ha `return_percent: Decimal | None` (assente senza valori registrati nel periodo); la risposta delle
  statistiche dell'API lo porta.
- Il pannello delle statistiche della dashboard mostra «Rendimento» con il colore di guadagno e perdita condiviso.

## Conseguenze

- Statistiche e riepilogo coincidono con «Dall'inizio»; su un periodo più corto il rendimento è quello del periodo.

## Prove

- Scenari in R2.2.6 (api: rendimento del periodo con un incasso nel periodo; dashboard: il pannello mostra il rendimento)
  e in R3.4.3 (api: con «Dall'inizio» uguale al riepilogo). Unit test del calcolo sulla finestra.
