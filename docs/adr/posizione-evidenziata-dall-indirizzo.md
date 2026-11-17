# ADR posizione-evidenziata-dall-indirizzo — La posizione indicata dall'indirizzo si evidenzia nella scheda

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.6, Task 589
- Collegate: ADR destinazioni-delle-notifiche-nella-dashboard, ADR 0119, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

Le schede Posizioni (`features/flow-positions/components/open-positions.tsx`, riga per asset) e Posizioni chiuse
(`closed-positions.tsx`, riga per istante di chiusura e asset, paginata, più recenti prima) non sanno evidenziare una
posizione arrivando da un link.

## Fattori decisionali

- R3.5.6: la scheda si apre con la posizione evidenziata.
- Le righe non hanno un id: si identificano come oggi (asset; istante di chiusura e asset).
- Accessibilità: evidenza con colore e testo (non solo colore), focus sulla riga.

## Decisione

- Posizioni: parametro `asset` dell'indirizzo; la riga di quell'asset è evidenziata (sfondo e `aria-current="true"`),
  portata in vista e messa a fuoco.
- Posizioni chiuse: parametri `asset` e `closed_at`; stessa evidenza sulla riga corrispondente della pagina caricata
  (la prima, dove sta una chiusura appena notificata). Se la riga non è nella pagina, un avviso con il collegamento
  allo Storico filtrato per flusso e asset.
- Il supporto sta nel componente condiviso della tabella (`DataTable`: prop facoltativa della riga evidenziata) per non
  duplicarlo.
- Prove: unit test delle due schede (riga evidenziata, riga assente) e di `DataTable`.

## Alternative scartate

- Pagina di dettaglio della singola operazione: scartata dal proprietario.

## Conseguenze

- Ogni tabella può evidenziare una riga con la stessa prop.
