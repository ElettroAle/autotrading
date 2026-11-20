# ADR cache-delle-letture-del-conto-come-decorator-in-memoria — Letture del conto per la dashboard da un decorator con cache nella memoria del processo api

- Stato: proposta (20 novembre 2026)
- Requisiti: Bug 635 (Task 638); R1.6.1, R1.7.3, R6.4.2
- Collegate: ADR 0021 (api e worker via HTTP interno), ADR 0007; `.claude/rules/layer-adapters.md`,
  `.claude/rules/tech-worker.md`, `.claude/rules/tech-threads.md`
- Verifica: prova

## Contesto e problema

Nel processo `api` la porta `AccountActivityPort` la realizza `WorkerAccountActivityAdapter`: ogni chiamata chiede al
worker una lettura completa di Hyperliquid (6 chiamate in serie, 2,2–2,8 s misurati in dev il 20 novembre 2026).
L'elenco dei flussi la ripete per ogni flusso dello stesso conto (circa 5 s con 2 flussi), la pagina Conti rilegge il
conto per il capitale libero, e la dashboard aggiorna ogni 30 s. In `api` questa porta serve solo le richieste della
dashboard: i cicli girano nel worker e leggono Hyperliquid con i propri adapter.

## Fattori decisionali

- Decisioni del proprietario (20 novembre 2026, in chat, analisi del Bug 635):
  - punto 4: cache breve delle letture del conto solo per la dashboard, validità 10 secondi;
  - la cache è un adapter decorator con la stessa interfaccia, in una cartella propria (`process_memory/`), montato
    dalla composition; nessuna dipendenza tra cartelle adapter;
  - punto 2 (una lettura per conto nell'elenco dei flussi): coperto dal decorator, senza toccare i casi d'uso;
  - la regola diventa parte del contratto nella stessa PR.
- CLAUDE.md: il decorator è l'unica eccezione per cui un adapter riceve una porta, la stessa che dichiara tra le basi;
  `bootstrap.py` istanzia e collega senza decisioni.
- `tech-threads.md`: in `threads/` si avviano thread. Il lock interno di un archivio non avvia thread.
- Valore per cui il proprietario non vuole stato nascosto: lo stato sta solo nell'archivio della cache, creato una
  volta dalla composition, in RAM, perso al riavvio.

## Decisione

- Cartella nuova `adapters/outbound/process_memory/`: il sistema integrato è la memoria del processo. Nessuna libreria
  esterna.
- `ProcessMemoryAccountActivityAdapter(AccountActivityPort)`: decorator legato al tenant della richiesta; riceve
  l'adapter della stessa porta da decorare. Una lettura del conto resta valida 10 secondi dall'istante in cui è
  arrivata; entro la validità risponde dall'archivio, altrimenti chiama la porta decorata e salva la risposta. Un
  errore della porta decorata non si salva e passa invariato.
- L'archivio è privato della cartella, uno per processo, creato dalla funzione di composizione
  `process_memory_adapters()`, che restituisce la funzione che decora una porta per un tenant. Chiave: tenant e conto.
  Un lock protegge l'archivio dalle richieste concorrenti; le voci scadute si tolgono alla scrittura.
- `bootstrap.py`, solo nella composition del processo `api`, decora l'adapter `worker/` della lettura del conto con
  quella funzione. Il worker non la monta: i cicli leggono sempre l'exchange.
- La durata di 10 secondi è nella configurazione della cartella (`_ProcessMemorySettings`) con quel default.
- Contratto, nella stessa PR: in `CLAUDE.md` e in `layer-adapters.md` una cache è un decorator della stessa porta in
  una cartella propria, montato dalla composition, con il suo stato creato una volta dalla composition; in
  `tech-threads.md` il lock interno di un archivio non è avviare thread; nuova `tech-process-memory.md`, cartella
  nell'elenco e riga nell'indice delle rule.

## Alternative scartate

- Campi `activity` facoltativi nei comandi dell'elenco dei flussi: cambia i casi d'uso per un problema di accesso
  all'exchange, e non copre pagina Conti né refresh.
- Cache dentro l'adapter `worker/`: mescola trasporto e memoria nella stessa cartella.
- Cache nel worker: vedrebbero dati vecchi anche i cicli.
- Libreria esterna di cache: non serve per un dizionario con scadenza.

## Conseguenze

- L'elenco dei flussi legge una volta per conto; la pagina Conti non rilegge il conto entro 10 secondi; i refresh
  ravvicinati non chiamano il worker.
- Dopo un'azione dalla dashboard (chiusura, emergenza) la lettura del conto può restare vecchia al più 10 secondi.
- Con più repliche di `api` ogni processo ha il suo archivio: oggi ce n'è una.
