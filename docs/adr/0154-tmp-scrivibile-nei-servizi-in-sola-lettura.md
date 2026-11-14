# ADR 0154 — Cartella temporanea scrivibile nei servizi in sola lettura

- Stato: proposta (14 novembre 2026)
- Requisiti: Bug 272 (Task 273)
- Collegate: ADR 0148 (LiteLLM come libreria nel worker), ADR 0107 (forecaster con `/tmp` in tmpfs)

## Contesto e problema

Dopo l'ADR 0148 il worker non parte: all'import, `litellm` chiama `tempfile.gettempdir()` e il container, in sola
lettura, non ha una cartella temporanea scrivibile («No usable temporary directory found»). Il rilascio dev fallisce.
`migrate`, `api` e `dashboard` sono nella stessa condizione: oggi non scrivono file temporanei, ma qualsiasi libreria
aggiornata potrebbe farlo.

## Fattori decisionali

- ADR 0107: il forecaster gira in sola lettura con `/tmp` in tmpfs; è la forma già scelta nel progetto.
- `CLAUDE.md`: il deploy passa dalla pipeline; i container restano in sola lettura.

## Opzioni considerate

### 1. `/tmp` in tmpfs su ogni servizio in sola lettura

- Pro: stessa forma del forecaster; il filesystem resta in sola lettura; la cartella sparisce al riavvio.
- Contro: qualche riga in più nel compose.

### 2. `/tmp` in tmpfs solo nel worker

- Pro: tocca il solo servizio che oggi ne ha bisogno.
- Contro: lo stesso guasto torna al prossimo aggiornamento di una libreria in un altro servizio.

### 3. Disattivare il filesystem in sola lettura del worker

- Pro: nessuna configurazione.
- Contro: toglie una difesa del servizio che apre le chiavi.

## Esito della decisione

Opzione 1. Ogni servizio del compose con `read_only: true` dichiara `tmpfs: [/tmp]`. Una prova sul compose rifiuta un
servizio in sola lettura senza `/tmp` in tmpfs.

Verifica: prova (`tests/unit/deploy/test_installation.py`).

### Conseguenze

- I file temporanei vivono in memoria e spariscono al riavvio del container.
