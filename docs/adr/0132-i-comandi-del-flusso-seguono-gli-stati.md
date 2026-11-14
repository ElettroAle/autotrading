# ADR 0132 — I comandi del flusso seguono gli stati ammessi e chiedono conferma per fermo e archiviazione

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.3.4 (Task T2.3.4.1)
- Collegate: ADR 0116, ADR 0119; R1.1.2 (`POST /flows/{id}/{action}`), R1.1.5 (`POST /flows/{id}/stop`),
  R1.1.6 (`POST /flows/{id}/archive`)

## Contesto e problema

Dalla pagina del flusso l'utente avvia, mette in pausa, riprende, ferma e archivia. Le transizioni ammesse sono
regole del dominio.

## Decisione

- I pulsanti visibili dipendono dallo stato restituito dall'API secondo la tabella delle transizioni del dominio,
  ricopiata in un solo modulo della funzionalità `flow-commands`; un comando rifiutato dall'API mostra il suo
  Problem Details, così l'API resta l'autorità anche se la copia divergesse.
- Fermo e archiviazione chiedono conferma; la finestra di fermo elenca le posizioni aperte del flusso dallo stato.
- Dopo ogni comando si invalidano le query del flusso.

## Alternative scartate

- **Azioni ammesse restituite dall'API**: nessuna copia della tabella, ma un cambio di contratto per un beneficio
  piccolo con pochi stati.

## Conseguenze

- Uno stato nuovo nel dominio richiede di aggiornare il modulo della tabella.
