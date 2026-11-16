# ADR equity-curve-larga-come-lo-schermo — Equity curve larga come lo schermo, senza scorrimento orizzontale

- Stato: proposta (16 novembre 2026)
- Requisiti: Bug 498, Task 499
- Collegate: ADR 0121 (grafici con Recharts), ADR intervallo-trascinando-sull-equity-curve, ADR
  dashboard-leggibile-su-mobile

## Contesto e problema

Su telefono l'equity curve è più larga dello schermo e scorre di lato, ma il trascinamento sul grafico seleziona
l'intervallo: il grafico non si riesce a scorrere (dev, 16/11/2026).

## Fattori decisionali

- Decisione del proprietario (16/11/2026): il grafico occupa la larghezza disponibile, senza scorrimento orizzontale; il
  trascinamento seleziona e la pagina scorre in verticale; con molti punti date principali e punti più piccoli.
- ADR 0121: Recharts solo nei grafici condivisi di `src/components/charts`; componenti riusabili.

## Opzioni considerate

1. Il grafico condiviso dell'equity non ha una larghezza minima legata al numero dei punti: segue sempre la larghezza
   del contenitore (`ResponsiveContainer` al 100%), senza riquadro scorrevole; le tacche dell'asse del tempo si
   diradano da sole (`minTickGap`) e il raggio dei punti scende quando i punti sono molti rispetto alla larghezza.
   `touch-action: pan-y` resta sulla figura dove la selezione è offerta.
2. Pressione lunga o comando di selezione: scartati dal proprietario.

## Esito della decisione

Opzione 1.

Verifica: prova (prova di layout a 360 px: nessuno scorrimento orizzontale del grafico con molti punti; unit test del
raggio dei punti secondo la densità).

### Conseguenze

- Il grafico si legge intero su ogni schermo; il dettaglio di un tratto si ottiene selezionando l'intervallo.
