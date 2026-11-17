# ADR grafici-condivisi-larghi-come-lo-schermo — Una sola cornice responsive per tutti i grafici

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 593, Task 595
- Collegate: ADR 0121 (grafici con Recharts), ADR equity-curve-larga-come-lo-schermo, ADR
  dashboard-leggibile-su-mobile, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

`components/charts/comparison-chart.tsx` disegna un `LineChart` largo 720 px fissi dentro una figura
`overflow-x-auto`; `equity-chart.tsx` usa `ResponsiveContainer` al 100%, `minTickGap` e un'altezza sua. La regola
dell'ADR equity-curve-larga-come-lo-schermo è stata applicata a un solo grafico perché la larghezza, l'asse del tempo e
il tooltip sono ripetuti in ogni grafico invece di stare in un componente condiviso. Il proprietario (17/11/2026): i
grafici responsive si devono comportare tutti uguali.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): stesso comportamento per tutti i grafici.
- ADR equity-curve-larga-come-lo-schermo: larghezza del contenitore, nessuno scorrimento orizzontale, date diradate.
- ADR 0121 e tech-dashboard.md: Recharts solo in `components/charts`, componenti riusabili, nessuna copia.
- Recharts 3 registra assi e tooltip dal contesto del grafico: possono stare in componenti propri.

## Decisione

- Nuovo modulo condiviso `components/charts/chart-frame.tsx` con ciò che ogni grafico ha in comune:
  - `ChartFrame`: la figura col nome accessibile e il `ResponsiveContainer` al 100% della larghezza, altezza unica
    (320 px), dimensione iniziale e `onResize` facoltativo per chi adatta i punti alla larghezza;
  - `TimeAxis`: asse del tempo numerico con le date del giorno e `minTickGap` comune;
  - `ChartTooltip`: tooltip che resta dentro il grafico (`allowEscapeViewBox` falso) con larghezza massima e testo che
    va a capo, così nomi lunghi non escono dallo schermo.
- `EquityChart` e `ComparisonChart` usano i tre componenti; spariscono `WIDTH`, l'`overflow-x-auto` e le costanti
  duplicate. Il confronto adatta anche il raggio dei punti alla larghezza con la stessa funzione dell'equity
  (`dotRadius`), spostata nel modulo condiviso.
- `tech-dashboard.md`: ogni grafico di `components/charts` si disegna dentro `ChartFrame` con `TimeAxis` e
  `ChartTooltip`; nessuna larghezza fissa.
- Prove: unit test di `ChartFrame`, `TimeAxis`, `ChartTooltip` e dei due grafici; prova di layout a 360 px per entrambi
  i grafici (nessuno scorrimento orizzontale, tooltip dentro lo schermo); prova che nessun file di `components/charts`
  passa una `width` numerica a un grafico Recharts.

## Alternative scartate

- Correggere solo il confronto copiando la soluzione dell'equity: lascia due copie che divergeranno di nuovo.
- Un solo componente grafico generico per area e linee: i due grafici hanno interazioni diverse (selezione
  dell'intervallo, eventi, più serie); basta condividere ciò che decide il comportamento responsive.

## Conseguenze

- Un grafico nuovo nasce responsive usando la cornice; il comportamento si cambia in un punto solo.
