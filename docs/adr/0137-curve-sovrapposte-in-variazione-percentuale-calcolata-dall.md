# ADR 0137 — Curve sovrapposte in variazione percentuale calcolata dall'API

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.4.3 (Task T2.4.3.1)
- Collegate: ADR 0120 (`GET /flows/{flow_id}/equity`), ADR 0121 (Recharts), ADR 0123, ADR 0136; RF-23.08

## Contesto e problema

Fino a 5 curve sullo stesso grafico, ciascuna come variazione percentuale rispetto all'equity del suo primo punto
nel periodo. La variazione è un calcolo sui dati di business: non si fa nel frontend.

## Decisione

- La serie di equity del dominio (ADR 0120) espone per ogni punto la variazione percentuale dal primo punto del
  periodo; `GET /flows/{flow_id}/equity` la aggiunge a ogni punto (`change_percent`, stringa con due decimali).
- Funzionalità `equity-comparison`: una query per flusso scelto (al più 5), grafico a linee Recharts sull'asse del
  tempo con un colore distinto per flusso da una palette fissa accessibile e legenda col nome.
- I flussi scelti e il periodo arrivano dalla query string (ADR 0136).

## Alternative scartate

- **Variazione calcolata nel browser**: nessun cambio di API, ma il calcolo vive fuori dal dominio.
- **Endpoint unico per più flussi**: una sola chiamata, ma un secondo modo di leggere la stessa serie.

## Conseguenze

- La curva del singolo flusso e quella sovrapposta leggono lo stesso endpoint.
