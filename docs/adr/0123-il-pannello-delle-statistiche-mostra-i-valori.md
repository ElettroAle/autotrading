# ADR 0123 — Il pannello delle statistiche mostra i valori dell'API senza ricalcolarli

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.6 (Task T2.2.6.2)
- Collegate: ADR 0116 (struttura della dashboard), ADR 0119 (client generato e rilettura), ADR 0122

## Contesto e problema

Il pannello delle statistiche ha una scelta del periodo che serve anche all'equity curve (R2.2.3) e alla
classifica (R2.4.2), e mostra numeri che l'API restituisce come stringhe.

## Decisione

- Funzionalità `flow-statistics` in `src/features`, con query TanStack sulla chiave (flusso, periodo).
- Selettore del periodo come componente condiviso in `src/components/ui/period-selector`, con il periodo nella
  query string della pagina, così il periodo scelto sopravvive al ricaricamento e lo leggono anche gli altri
  pannelli della stessa pagina.
- Nessun calcolo: i valori si formattano in italiano (`Intl.NumberFormat('it-IT')`), «non disponibile» quando il
  win rate è `null`.

## Alternative scartate

- **Periodo nello stato locale del pannello**: più semplice, ma ogni pannello della pagina avrebbe il suo e si
  perde al ricaricamento.

## Conseguenze

- Equity curve e classifica usano lo stesso selettore e lo stesso parametro.
