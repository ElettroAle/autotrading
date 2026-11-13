# ADR 0043 — Previsione del prezzo con lo smorzamento di Holt nel domain

- Stato: superata da ADR 0107 (13 novembre 2026)
- Requisiti: R1.3.5 (Task T1.3.5.1, T1.3.5.2)

## Contesto

La fonte forecast dà all'agente, per ogni asset del flusso, una previsione del prezzo a 15 minuti e a 1 ora
sullo storico dell'exchange, con profondità da 1 a 90 giorni (predefinita 7). Ogni previsione si registra e
allo scadere dell'orizzonte le si affianca il prezzo effettivo. L'architettura prevedeva in una fase successiva
un servizio `forecaster` con Prophet; il Task T1.3.5.1 chiede di misurare memoria, tempo e immagine di Prophet e
di alternative senza cmdstan sulla VM d2-2 (2 GB di RAM, condivisi da PostgreSQL, `api` e `worker`), e ricorda che
un aumento della VM richiede l'approvazione del proprietario.

Misure sulla macchina di sviluppo, con uno storico di 7 giorni a un minuto (10080 punti), Python 3.15:

| Modello | Tempo (adattamento e previsione) | Memoria | Dipendenze installate |
|---------|----------------------------------|---------|-----------------------|
| Prophet 1.5.0 | 7,7 s | circa 135 MB nel processo, più il processo cmdstan | circa 215 MB (prophet 48, pandas 51, matplotlib 28, numpy 25, cmdstanpy) |
| Holt (trend lineare), griglia di 81 coppie di smorzamento | 0,27 s | trascurabile | nessuna |

Hyperliquid conserva solo le ultime 5000 candele di ogni intervallo: lo storico di 7 giorni arriva a 3 minuti
(3361 punti), quello di 90 giorni a 30 minuti (4321 punti). Prova dal vivo sulla testnet: 7 giorni in 0,27 s
per i due orizzonti, 90 giorni in 0,36 s.

## Decisione

- **Modello**: smorzamento esponenziale di Holt con trend lineare, in `domain/sources/holt_forecast.py`, solo
  libreria standard. Le costanti di smorzamento del livello e del trend sono la coppia, su una griglia da 0,1 a
  0,9, con il minor errore quadratico della previsione a un passo sullo storico stesso.
- **Orizzonte in passi**: l'orizzonte diviso per la distanza media tra i punti, anche frazionario; la stessa
  regola vale per ogni intervallo di candele.
- **Previsione** (`PriceForecast`): flusso, asset, orizzonte, istante, ultimo prezzo, prezzo previsto (con due
  decimali in più dell'ultimo prezzo), giorni di storico usati, storico ridotto, prezzo effettivo. La variazione
  percentuale si arrotonda a due decimali.
- **Storico ridotto**: lo storico è ridotto quando il primo punto è più recente della profondità richiesta di
  oltre una distanza tra punti; i giorni dichiarati sono allora quelli coperti, arrotondati per eccesso.
- **Prezzi** dall'adapter `HyperliquidPriceHistoryAdapter` (`adapters/outbound/hyperliquid/market_data.py`),
  con l'SDK ufficiale e senza credenziali: candele all'intervallo più fine che l'exchange conserva per tutta la
  profondità (1, 3, 5, 15, 30 minuti, 1 ora), lette a pagine dall'ultima ricevuta (al massimo 20), prezzo di
  chiusura all'istante di chiusura; il prezzo effettivo è il prezzo medio corrente (`allMids`). Ogni errore
  dell'exchange o risposta di forma inattesa diventa `SourceUnavailableError("forecast")`.
- **Casi d'uso**: `ForecastAssetUseCase` (previsioni dei due orizzonti e registrazione) e
  `RecordActualPricesUseCase` (prezzo effettivo delle previsioni scadute; un asset senza prezzo resta per il
  passaggio successivo, con un avviso nel log), sulle porte `PriceHistoryPort` e `ForecastRepositoryPort`.

## Alternative scartate

- **Prophet in un container `forecaster`**: un servizio in più nel Compose e una VM probabilmente più grande
  (d2-4), per una previsione che non è da sola un segnale di trading ma una fonte tra le altre, pesata dal
  flusso; 7,7 s per asset e ciclo su 2 vCPU condivise.
- **Prophet nell'immagine unica**: `api`, `worker` e `migrate` usano la stessa immagine; 215 MB di dipendenze
  scientifiche e il compilatore Stan entrerebbero in tutti i processi.
- **Alternative di libreria senza cmdstan** (statsmodels, statsforecast, NeuralProphet): portano comunque numpy,
  pandas o torch nell'immagine unica, per un modello di Holt che nel domain sono poche righe di libreria
  standard.
- **Un intervallo fisso di candele**: con 5000 candele conservate, un intervallo di un minuto copre solo 3 giorni
  e uno di un'ora rende la previsione a 15 minuti una frazione di passo su ogni profondità.

## Conseguenze

- Nessun container nuovo, nessuna modifica all'immagine e nessun aumento della VM: la d2-4 pre-approvata non
  serve per questa fonte.
- La porta `PriceHistoryPort` e il registro delle previsioni restano validi se un modello più ricco sostituisce
  Holt (RF-08.05): cambia solo la regola del domain o si aggiunge un adapter di previsione.
- Il repository SQLAlchemy delle previsioni con la sua migrazione e il collegamento al ciclo (contesto
  dell'agente, passaggio del prezzo effettivo nel `worker`) arrivano con l'integrazione delle fonti nel ciclo
  (F1.2); fino ad allora gli scenari che partono da un ciclo restano `@wip`.
