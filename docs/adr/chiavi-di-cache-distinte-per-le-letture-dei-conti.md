# ADR chiavi-di-cache-distinte-per-le-letture-dei-conti — Chiavi di cache distinte per ogni lettura con schema proprio

- Stato: proposta (16 novembre 2026)
- Requisiti: Bug 437, Task 438
- Collegate: ADR 0119 (struttura bulletproof-react), `.claude/rules/tech-dashboard.md` (TanStack Query, zod)

## Contesto e problema

Tre funzionalità della dashboard (`accounts`, `flows`, `flow-editor`) leggono `GET /accounts`, ciascuna con uno schema
zod proprio e ridotto, sotto la stessa chiave di cache `['accounts']`. TanStack Query conserva il dato già validato
dallo schema di chi ha letto per primo: dopo una pagina del flusso, la pagina Conti riceve conti senza
`allocated_capital` e va in errore (`Cannot read properties of undefined (reading 'startsWith')`).

## Fattori decisionali

- Bulletproof-react: ogni funzionalità possiede le sue letture, nessun import tra funzionalità.
- La cache conserva il risultato della `queryFn`, cioè il dato già passato dallo schema.
- Registrare, rimuovere o sostituire un conto deve aggiornare tutte le letture dei conti.

## Opzioni considerate

1. Ogni lettura con uno schema proprio ha una chiave propria che comincia con la risorsa e poi nomina la funzionalità
   (`['accounts', 'flows']`, `['accounts', 'flow-editor']`); la lettura della funzionalità `accounts` resta
   `['accounts']`. Le mutazioni dei conti invalidano il prefisso `['accounts']`, che per TanStack Query comprende
   tutte le chiavi che cominciano così. Una prova unitaria verifica che nessuna chiave di query letterale si ripeta tra
   due funzionalità, e una prova riproduce il percorso pagina del flusso, poi pagina Conti.
2. Un unico schema completo dei conti condiviso: scartato, crea un import tra funzionalità o un modulo condiviso
   con il contratto di una sola.

## Esito della decisione

Opzione 1.

Verifica: prova (unit test sulle chiavi delle query di tutte le funzionalità; test che apre un flusso e poi i Conti).

### Conseguenze

- Una lettura nuova con schema proprio non può riusare la chiave di un'altra senza far fallire la prova.
