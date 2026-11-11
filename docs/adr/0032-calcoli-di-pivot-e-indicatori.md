# ADR 0032 — Calcoli di pivot e indicatori: Decimal nel domain, senza librerie

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.3.3, R1.3.4 (Task T1.3.3.1, T1.3.4.1)

## Contesto

R1.3.3 chiede EMA20, EMA50, MA20, MA50, MACD, RSI a 7 e 14 periodi e volume su due timeframe, come valore
corrente e come serie degli ultimi valori. R1.3.4 chiede i pivot classici della giornata UTC precedente, la
posizione del prezzo rispetto al PP e la distanza percentuale dal supporto e dalla resistenza più vicini. La rule
`context-sources.md` mette i calcoli nel domain, che usa solo la libreria standard. `docs/architecture.md`
nominava pandas-ta. La raccolta dei prezzi e la composizione del contesto arrivano con i cicli (F1.2).

## Decisione

- **Calcoli nel domain di `sources`, in `Decimal`**: `pivot_levels.py` (`DailyRange`, `PivotLevels.of`,
  `reading_at` con `PricePosition` sopra, sotto o sul PP, `NearestLevel` con distanza in percentuale del prezzo)
  e `technical_indicators.py` (`simple_moving_average`, `exponential_moving_average`, `macd`,
  `relative_strength_index`, `last_values`).
- **Definizioni**:
  - EMA inizializzata con la media semplice del primo periodo, smorzamento 2 / (periodo + 1).
  - MACD con EMA12 − EMA26, segnale EMA9 della linea, istogramma pari alla differenza.
  - RSI di Wilder: medie di guadagni e perdite del primo periodo, poi smorzamento (periodo − 1) / periodo.
    Senza perdite vale 100, prezzi fermi valgono 50.
  - Un prezzo uguale a un livello lo ha come supporto; la resistenza è il primo livello strettamente sopra.
- **Storico insufficiente**: `InsufficientHistoryError` con quanti valori servono e quanti ce ne sono. Il ciclo
  tratterà la fonte come assente (R1.2.5).

## Alternative scartate

- **pandas-ta (o pandas)**: dipendenza pesante nel domain, vietata dalla regola delle dipendenze, e calcoli in
  `float` per formule che si scrivono in poche righe.
- **Calcolo nell'adapter dell'exchange**: le formule sono regole del requisito, non della tecnologia. Restano
  testabili senza rete.

## Conseguenze

- Gli scenari di R1.3.3 e R1.3.4 restano `@wip` finché i cicli non compongono il contesto. Le US restano attive.
- `docs/architecture.md` §6.1 nomina ancora pandas-ta: vale questa ADR.
