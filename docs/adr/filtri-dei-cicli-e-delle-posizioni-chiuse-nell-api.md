# ADR filtri-dei-cicli-e-delle-posizioni-chiuse-nell-api — Filtri dei cicli e delle posizioni chiuse nell'API

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.4 (425), Task T6.4.4.1 (426)
- Collegate: R2.2.7 (cicli del flusso), R2.2.5 (posizioni chiuse), R2.5.1 (storico)

## Contesto e problema

`GET /flows/{flow_id}/cycles` accetta solo `page`; le posizioni chiuse del flusso accettano asset e intervallo ma
non direzione né risultato. R6.4.4 chiede di filtrare i cicli per esito e decisione e le posizioni chiuse per
direzione, risultato e asset, con il conteggio dei risultati; R6.4.3 chiede l'intervallo da-a su tutte le letture
della pagina del flusso.

## Fattori decisionali

- `CLAUDE.md`: un caso d'uso per modulo, porte nel contesto, RLS nell'adapter PostgreSQL.
- `.claude/rules/tech-dashboard.md`: la dashboard filtra solo ciò che l'API espone (nessun filtro lato client sui dati
  paginati).

## Opzioni considerate

1. Parametri di query opzionali sulle letture esistenti: cicli con `outcome` (concluso, fallito), `decision`
   (apertura, chiusura, mantenimento, nessuna), `from`, `to`; posizioni chiuse con `side` e `result` (vinta, persa)
   oltre ai filtri esistenti; ogni risposta paginata porta il totale dei risultati. I valori ammessi sono tipi del
   domain; un valore sconosciuto è un errore 400 del progetto.
2. Filtrare nella dashboard: scartata, rompe la paginazione.

## Esito della decisione

Opzione 1, nei casi d'uso esistenti (`list_cycles.py`, lettura delle posizioni chiuse) e nei loro adapter
SQLAlchemy, con indici se il piano lo richiede.

Verifica: prova (unit test dei casi d'uso, test di integrazione su PostgreSQL dei filtri e del totale, test dell'API).

### Conseguenze

- La dashboard può filtrare cicli e posizioni chiuse e mostrarne il numero.
