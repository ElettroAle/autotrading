# ADR errore-medio-della-previsione-nell-api — Errore medio della previsione letto dal contesto flows

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.6.1 (470), Task T3.6.1.1 (496)
- Collegate: R1.3.5 (previsioni e prezzo effettivo registrati), ADR 0042 (previsioni nel database), R2.2.6 (periodo
  delle statistiche)

## Contesto e problema

Le previsioni del forecast si registrano con il prezzo effettivo accanto allo scadere dell'orizzonte
(`RecordActualPricesUseCase`, contesto `sources`). Manca il loro errore: per flusso, asset e orizzonte, nel periodo
scelto, errore medio assoluto e percentuale, previsioni valutate e non valutabili. Gli orizzonti sono 15 minuti e
1 ora (R1.3.5): lo scenario «a 4 ore» dei criteri diventa «a 15 minuti».

## Fattori decisionali

- CLAUDE.md, niente ponti tra contesti: il contesto che usa un dato di un altro dichiara la sua porta, l'adapter della
  tecnologia che ha il dato la realizza.
- La pagina del flusso e il suo periodo appartengono a `flows` (`StatisticsPeriod`, `TimeWindow`).
- Nessun calcolo di business nella dashboard: l'API dà i valori già calcolati.

## Opzioni considerate

1. Nel contesto `flows`: porta `FlowForecastsPort` (`expired_forecasts(flow_id, now)`: le previsioni scadute del
   flusso come `EvaluatedForecast` di `domain/flows`, con asset, orizzonte in minuti, istante di scadenza, prezzo
   previsto e prezzo effettivo o nessuno), realizzata dall'adapter sqlalchemy delle previsioni. Il dominio
   `ForecastAccuracy` raggruppa per asset e orizzonte le previsioni scadute nel periodo (istante di scadenza nella
   finestra): errore medio assoluto, errore medio percentuale sul prezzo effettivo con due decimali, valutate (con
   prezzo effettivo) e non valutabili (senza); senza valutate le medie sono assenti. Una coppia asset-orizzonte che il
   flusso ha previsto ma che nel periodo non ha previsioni scadute compare con zero valutate. Caso d'uso
   `ReadForecastAccuracyUseCase`, rotta `GET /flows/{flow_id}/forecast-accuracy` con `period`, `from`, `to` come le
   statistiche; importi come testo, media percentuale con due decimali, `null` quando non disponibile.
2. Un caso d'uso nel contesto `sources` letto dalla pagina del flusso: scartato, il periodo e la pagina sono di
   `flows` e servirebbe un ponte.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.6.1 sul caso d'uso con adapter finti, unit test del dominio e della rotta, test di
integrazione dell'adapter su PostgreSQL).

### Conseguenze

- La qualità del forecast si legge dove si sceglie quanto pesarlo, senza toccare il servizio forecaster.
