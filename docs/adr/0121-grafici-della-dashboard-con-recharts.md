# ADR 0121 — Grafici della dashboard con Recharts

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.3 (Task T2.2.3.2); usata anche da R2.4.3
- Collegate: ADR 0116 (una sola libreria di grafici, scelta dal primo lavoro che ne ha bisogno), RF-23.01

## Contesto e problema

L'equity curve ha linea e area verdi sopra il capitale iniziale e rosse sotto; le curve sovrapposte (R2.4.3)
mettono fino a cinque serie sullo stesso asse. ADR 0116 lascia la scelta della libreria al primo lavoro che la usa.

## Decisione

Recharts: componenti React dichiarativi in SVG, `AreaChart` con gradiente diviso sul valore di riferimento per
il verde e il rosso, `ReferenceLine` per il capitale iniziale, tooltip e legenda accessibili. Il componente
condiviso sta in `src/components/charts`, i dati arrivano dalle funzionalità.

## Alternative scartate

- **Chart.js (react-chartjs-2)**: canvas, meno verificabile con Testing Library e Playwright.
- **ECharts**: molto completo, ma pesante per due tipi di grafico.
- **D3 a mano**: massimo controllo, molto codice da provare.

## Conseguenze

- La rule `tech-dashboard.md` nomina Recharts come unica libreria di grafici.
