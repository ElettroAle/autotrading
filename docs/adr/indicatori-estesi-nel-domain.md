# ADR indicatori-estesi-nel-domain — Fibonacci, Gann e ciclo dominante nel domain

- Stato: proposta (19 novembre 2026)
- Requisiti: US 347 R5.1.4, Task 348
- Collegate: ADR 0032 (calcoli in Decimal nel domain), ADR 0057, ADR 0058, ADR fonti-con-adapter-dichiarati;
  `.claude/rules/context-sources.md`
- Verifica: prova

## Contesto e problema

R5.1.4 vuole tre indicatori selezionabili come parametri della fonte «indicatori», sulle candele chiuse del
timeframe lungo: ritracciamenti di Fibonacci tra minimo e massimo delle ultime N candele, angoli di Gann dal minimo o
massimo più recente, ciclo dominante (periodo e fase); N predefinito 100; storico corto dichiarato.

## Fattori decisionali

- Calcoli nel domain in Decimal sulle candele dell'exchange (ADR 0032, 0057); i parametri sono interi con limiti.

## Decisione

- **Parametri della fonte** (validi per ogni adapter): `fibonacci`, `gann`, `ciclo` da 0 a 1 (predefinito 0 =
  spento), `candele_estese` da 10 a 500 (predefinito 100). Le candele si leggono dal timeframe lungo esistente
  (4 ore), in numero pari al massimo tra la richiesta attuale e N.
- **Fibonacci**: livelli `massimo − r·(massimo − minimo)` per r = 23,6%, 38,2%, 50%, 61,8%, 78,6%.
- **Gann**: perno = l'estremo (minimo o massimo) più recente tra le N candele; unità di prezzo per candela = media del
  true range delle N candele; per 1x1, 1x2, 2x1 il valore della linea all'ultima candela chiusa, salendo dal minimo o
  scendendo dal massimo (1x2 = mezza unità per candela, 2x1 = doppia).
- **Ciclo dominante**: chiusure detrendizzate con la retta dei minimi quadrati, periodogramma (trasformata discreta)
  sui periodi da 4 a N/2 candele; periodo = picco di potenza, fase in gradi da 0 a 360 all'ultima candela.
- Storico più corto di N: calcolo sulle candele disponibili e nota «storico di X candele, meno delle N richieste».

## Alternative scartate

- Ciclo con autocorrelazione: meno stabile su serie brevi e senza fase.

## Conseguenze

- Il catalogo della fonte cresce di quattro parametri; l'editor li genera da solo.
