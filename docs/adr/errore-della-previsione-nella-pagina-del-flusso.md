# ADR errore-della-previsione-nella-pagina-del-flusso — Errore della previsione nella Panoramica del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.6.1 (470), Task T3.6.1.2 (497)
- Collegate: ADR errore-medio-della-previsione-nell-api, ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune, ADR
  liste-etichetta-valore-che-vanno-a-capo

## Contesto e problema

La pagina del flusso deve mostrare, nel periodo scelto in cima, l'errore della previsione per asset e orizzonte.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): componenti riusabili, nessun duplicato per pagina.
- Periodo unico in cima alla pagina, condiviso dalle schede (ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune).
- Nessun calcolo nella dashboard: i valori arrivano dall'API.

## Opzioni considerate

1. Un riquadro «Errore della previsione» nella Panoramica, dopo le statistiche, della funzionalità `flow-statistics`:
   lettura di `GET /flows/{flow_id}/forecast-accuracy` con il periodo della pagina; per ogni asset e orizzonte una voce
   della lista etichetta-valore condivisa («BTC · 1 ora»: «errore medio 450 · 0,74% · 2 previsioni valutate», più
   «N non valutabili» se maggiori di zero, oppure «non disponibile nel periodo»). Il riquadro non compare se il flusso
   non ha previsioni.
2. Una scheda a sé: scartata, è un dato di sintesi accanto alle statistiche.

## Esito della decisione

Opzione 1.

Verifica: prova (scenario «Errore nella pagina del flusso» di R3.6.1, unit test del componente).

### Conseguenze

- Statistiche ed errore della previsione si leggono insieme, nello stesso periodo.
