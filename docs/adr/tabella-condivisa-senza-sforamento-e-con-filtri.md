# ADR tabella-condivisa-senza-sforamento-e-con-filtri — Tabella condivisa senza sforamento, righe cliccabili e filtri

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.4 (425), Task T6.4.4.2 (427) e T6.4.4.3 (428)
- Collegate: ADR liste-etichetta-valore-che-vanno-a-capo, ADR filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api

## Contesto e problema

Posizioni chiuse e classifica dei flussi hanno 9-10 colonne: su un telefono in vista larga allargano la pagina e il
browser rimpicciolisce tutto (schermate del 16/11/2026). Le righe dei cicli sono cliccabili solo sull'istante. Non
c'è un modo comune per filtrare una tabella.

## Fattori decisionali

- R6.4.4: nessuna tabella allarga la pagina, riga intera cliccabile, filtri dichiarati dalla tabella nell'indirizzo.
- Decisione del proprietario (16/11/2026): usabilità prima, filtri nel componente se le tabelle lo condividono.
- Componente esistente `DataTable` (schede sotto 768 pixel).

## Opzioni considerate

1. Evolvere `DataTable`: schede sotto 768 pixel (come oggi); sopra, contenitore con scorrimento orizzontale interno
   e prima colonna fissa; proprietà per la destinazione di una riga (tutta la riga cliccabile, con collegamento
   accessibile); barra dei filtri dichiarata dalla tabella (scelte rapide, conteggio dei risultati dall'API,
   azzeramento) con lo stato nell'indirizzo. Cicli, posizioni chiuse e classifica la usano.
2. Nascondere colonne per priorità: scartata, toglie dati senza che l'utente lo sappia.

## Esito della decisione

Opzione 1. La prova di layout misura anche a 900 pixel con dati a molte colonne.

Verifica: prova (scenari di R6.4.4, unit test del componente, prova di layout a 360 e 900 pixel).

### Conseguenze

- Ogni tabella nuova eredita comportamento su telefono, righe cliccabili e filtri.
