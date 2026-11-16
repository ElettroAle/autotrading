# ADR formato-dei-prezzi-condiviso — Formato dei prezzi condiviso nella dashboard

- Stato: proposta (16 novembre 2026)
- Requisiti: Bug 431 (Task 433)
- Collegate: ADR 0116 (struttura della dashboard), R2.2.4 (posizioni aperte), R2.2.5 (posizioni chiuse)

## Contesto e problema

Le posizioni chiuse mostrano i prezzi medi con tutte le cifre del calcolo («63.996,0322580645161290322580»): la
colonna allarga la tabella oltre lo schermo (dev, 16/11/2026). Il prezzo arriva dall'API come stringa decimale e
la dashboard lo formatta senza limite di cifre.

## Fattori decisionali

- Bug 431: oltre 1000 due decimali, sotto al più 6 cifre significative; il valore completo resta nell'API e nel CSV.
- `.claude/rules/tech-dashboard.md`: la dashboard non aggiunge logica di business; la formattazione è presentazione.

## Opzioni considerate

1. Una funzione di formato dei prezzi condivisa in `src/utils`, con `Intl.NumberFormat` in italiano, usata da ogni
   colonna di prezzo (posizioni aperte e chiuse, storico, ordini, dettaglio del ciclo).
2. Arrotondare nell'API: scartata, il valore completo serve a CSV e calcoli.

## Esito della decisione

Opzione 1. Importi in valuta e percentuali restano col formato attuale.

Verifica: prova (unit test della funzione sui casi limite; scenario esistente delle posizioni chiuse con un prezzo
a molte cifre).

### Conseguenze

- I prezzi si leggono e non allargano più le tabelle.
