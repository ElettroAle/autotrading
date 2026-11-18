# ADR periodo-di-6-ore-e-dall-inizio — Periodo 6h e etichetta «Dall'inizio»

- Stato: proposta (18 novembre 2026)
- Requisiti: R6.4.7, Task 606
- Collegate: ADR periodi-brevi-come-durata-nel-dominio, ADR periodi-brevi-nel-selettore-condiviso, ADR
  periodi-brevi-nei-testi-dei-requisiti
- Verifica: prova

## Contesto e problema

Il proprietario (17/11/2026) vuole il periodo delle ultime 6 ore e «Dall'inizio» al posto di «Tutta la vita».

## Fattori decisionali

- I periodi brevi sono durate del domain (`StatisticsPeriodKind`, `LAST_DURATIONS`) e un solo elenco nella dashboard
  (`PERIODS` del selettore condiviso).
- Gli indirizzi salvati con `period=all` restano validi.

## Decisione

- Domain: `LAST_6_HOURS = "6h"` tra `1h` e `12h`, con la sua durata; l'API lo accetta ovunque accetta i periodi
  (pagina del flusso, classifica, storico), schema e client generato aggiornati.
- Dashboard: `PERIODS` aggiunge `{ kind: '6h', label: '6 ore' }` e l'etichetta di `all` diventa «Dall'inizio»; il
  valore `all` nell'indirizzo non cambia.
- Specifiche: R6.4.7 nel repository; i testi di R6.4.6, R2.2.6 e R2.4.2 che elencano i periodi si allineano, board
  compresa.
- Prove: unit test del domain e del selettore; scenari R6.4.7.

## Alternative scartate

- Cambiare anche il valore `all` nell'indirizzo: romperebbe gli indirizzi salvati senza beneficio.

## Conseguenze

- Il menu ha nove voci.
