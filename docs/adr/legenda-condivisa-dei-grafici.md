# ADR legenda-condivisa-dei-grafici — Legenda condivisa sotto i grafici, con i segni del grafico

- Stato: accettata (19 novembre 2026, design approvato dal proprietario)
- Requisiti: US 626 R6.5.6, Task 627
- Collegate: ADR 0121 (grafici), ADR grafici-condivisi-larghi-come-lo-schermo, ADR cicli-falliti-sull-equity-curve, ADR
  rendimento-composto-tra-le-variazioni-di-capitale, ADR 0137 (confronto); `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

`EquityChart` (`dashboard/src/components/charts/equity-chart.tsx`) disegna punti verdi e rossi, la linea tratteggiata
del capitale iniziale, croci rosse dei cicli falliti e rombi viola delle variazioni di capitale, senza legenda.
`ComparisonChart` ha una sua legenda privata (`Legend`) coi pallini dei flussi, passata a `ChartFrame` come `footer`.

## Fattori decisionali

- Proprietario (19/11/2026): legenda sotto i grafici del flusso, leggibile su telefono; croce e rombo in legenda solo
  se presenti nel periodo.
- Regole della dashboard: componenti condivisi, nessun duplicato (decisione del proprietario 16/11/2026); i grafici
  stanno in `ChartFrame`, largo quanto lo spazio, senza scorrimento orizzontale; il segno non si legge solo dal colore.

## Decisione

- Nuovo componente condiviso `ChartLegend` in `components/charts/chart-legend.tsx`: elenco `<ul aria-label="Legenda">`
  di voci `{ mark, label }`, dove `mark` è un piccolo SVG nascosto ai lettori di schermo; `flex flex-wrap` con spazi
  ridotti e testo `text-sm`, così su telefono va a capo e su desktop sta su una riga.
- I segni (punto, linea tratteggiata, croce, rombo) si definiscono una volta in `equity-chart.tsx` e servono sia al
  grafico sia alla legenda: stessa forma, stesso colore.
- `EquityChart` passa a `ChartFrame` il `footer` con `ChartLegend`: sempre «sopra il capitale iniziale», «sotto il
  capitale iniziale», «capitale iniziale»; «ciclo fallito» e «variazione di capitale» solo se `events` ne contiene
  almeno uno del loro tipo. Senza punti il grafico non c'è e nemmeno la legenda.
- `ComparisonChart` usa `ChartLegend` con un pallino del colore di ogni flusso al posto della `Legend` privata, che si
  elimina.
- Prova di architettura: un grafico di `components/charts` con una legenda la disegna con `ChartLegend`.

## Alternative scartate

- La legenda di Recharts: disegnata dentro l'SVG, non va a capo come il resto della pagina e non riusa i segni.
- Tutte le voci sempre: su telefono righe inutili quando il periodo non ha eventi (proprietario).

## Conseguenze

- Ogni grafico futuro con più segni ha la sua legenda con lo stesso componente.
