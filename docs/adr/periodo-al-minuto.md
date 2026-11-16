# ADR periodo-al-minuto — Periodo e intervallo al minuto in API e dashboard

- Stato: proposta (16 novembre 2026)
- Requisiti: Bug 500, Task 501 e 502
- Collegate: ADR intervallo-trascinando-sull-equity-curve e ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune
  (superate solo nella granularità a giorni interi), ADR filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api, R2.2.8

## Contesto e problema

L'intervallo (`from`, `to`) è a giorni interi UTC in tutte le letture con periodo (panoramica, stato, statistiche,
equity, classifica, storico, cicli, posizioni chiuse): trascinando tra due cicli dello stesso giorno si filtra l'intera
giornata. I 7 e 30 giorni degli elenchi partono dal giorno intero.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): intervallo al minuto ovunque si legga il periodo; etichetta con data e ora
  (es. «16/11 09:15 – 16/11 11:40»); 7 e 30 giorni da adesso.
- `.claude/rules/tech-dashboard.md`: stato del periodo nell'indirizzo; nessuna logica di business nella dashboard.

## Opzioni considerate

1. `from` e `to` diventano istanti (ISO 8601; senza fuso valgono UTC; una data sola vale la mezzanotte UTC). Il dominio
   tronca entrambi al minuto e considera compreso il minuto di `to`: la finestra va da `from` incluso a `to` + 1 minuto
   escluso (`TimeWindow.of_minutes`). `StatisticsPeriod`, `CycleFilter` e `ClosedPositionFilter` portano `since` e
   `until` al posto dei giorni. La dashboard scrive nell'indirizzo istanti UTC al minuto: il trascinamento dal primo
   all'ultimo istante scelto, il menu Intervallo con campi data e ora (`datetime-local`), gli elenchi dei 7 e 30 giorni
   da adesso; l'etichetta mostra data e ora nel fuso del browser.
2. Parametri nuovi accanto ai giorni: scartata, due modi per la stessa cosa.

## Esito della decisione

Opzione 1.

Verifica: prova (unit test del dominio: troncamento al minuto, minuto di `to` compreso, fuso mancante; test dell'API con
istanti; unit test della dashboard su indirizzo ed etichetta).

### Conseguenze

- Ogni pannello e ogni elenco della pagina leggono lo stesso intervallo al minuto.
