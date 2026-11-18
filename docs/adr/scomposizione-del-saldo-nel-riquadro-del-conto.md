# ADR scomposizione-del-saldo-nel-riquadro-del-conto — Saldo, valore dei flussi e capitale libero che tornano a vista

- Stato: proposta (18 novembre 2026)
- Requisiti: Bug 601, Task 602; R1.1.7, R3.3.2, R3.4.1
- Collegate: ADR capitale-libero-al-netto-del-valore-dei-flussi, ADR conti-a-riquadri, ADR
  stato-della-riconciliazione-nella-dashboard, ADR movimenti-non-spiegati-nel-riquadro-del-conto
- Verifica: prova

## Contesto e problema

Il riquadro del conto mostra Saldo (con il risultato aperto delle posizioni), Capitale allocato e Capitale libero; il
capitale libero toglie dal saldo il valore dei flussi (capitale allocato più risultato), che non si vede: 1013,49 −
300 non dà 704,56 e sembra che i guadagni vadano nel capitale libero (proprietario, 17/11/2026). Saldo atteso e
letto della riconciliazione escludono il risultato aperto, il Saldo no, senza che la pagina lo dica.

## Fattori decisionali

- ADR capitale-libero-al-netto-del-valore-dei-flussi: i guadagni restano dei flussi; la regola non cambia.
- Nessuna logica di business nella dashboard (ADR 0116): i valori della scomposizione li dà l'API.
- Stato visibile e testi chiari (tech-dashboard.md).

## Decisione

- Domain: `FreeCapital` porta anche `flows_value` (somma dei valori dei flussi che tengono il conto) oltre a `amount`;
  `FreeCapital.of` lo calcola con gli stessi stati.
- API: la risposta del capitale libero aggiunge `flows_value` e `flows_result` (valore dei flussi meno capitale
  allocato), client generato aggiornato.
- Dashboard, riquadro del conto, nell'ordine: «Saldo (con risultato aperto)», «Valore dei flussi» con sotto, più
  piccolo, «capitale allocato 300 + risultato +8,93» (risultato col colore e il segno del guadagno), «Capitale libero».
  Saldo = Valore dei flussi + Capitale libero si legge a vista. La sezione Riconciliazione dice sotto il titolo
  «Confronta il saldo senza il risultato delle posizioni aperte».
- Prove: unit test di domain, API e componenti (valori e testi).

## Alternative scartate

- Capitale libero come saldo meno capitale allocato: contraddice l'ADR capitale-libero-al-netto-del-valore-dei-flussi.
- Calcolare il risultato nella dashboard: logica di business fuori dall'API.

## Conseguenze

- I tre numeri del conto tornano senza calcoli a mente.
