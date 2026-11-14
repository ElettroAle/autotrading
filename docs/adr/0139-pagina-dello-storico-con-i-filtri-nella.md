# ADR 0139 — Pagina dello storico con i filtri nella query string

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.5.1 (Task T2.5.1.2)
- Collegate: ADR 0116, ADR 0119, ADR 0123 (selettore del periodo), ADR 0128 (`data-table`), ADR 0138

## Contesto e problema

La pagina dello storico ha tre schede (cicli, posizioni chiuse, ordini con esecuzioni) e filtri combinati; i
risultati arrivano a pagine con un cursore.

## Decisione

- Funzionalità `history`: scheda e filtri nella query string, così una ricerca ha un link e sopravvive al
  ricaricamento; il filtro per versione si abilita solo con un flusso scelto.
- `useInfiniteQuery` di TanStack con il cursore dell'API e pulsante «Carica altri»; nessuna rilettura automatica
  sulle pagine già caricate oltre la prima.
- Tabelle con `data-table`; gli ordini mostrano le esecuzioni in una riga espandibile.

## Alternative scartate

- **Filtri nello stato locale**: più semplice, ma nessun link alla ricerca.

## Conseguenze

- Nessuna logica di filtro nel browser: i risultati sono quelli dell'API.
