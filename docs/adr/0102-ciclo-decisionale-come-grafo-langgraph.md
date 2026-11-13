# ADR 0102 Ciclo decisionale come grafo LangGraph

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.2.1-R1.2.5, R1.3.x, R1.4.x, R1.5.x, R1.6.x, R1.7.x, R1.8.x (Bug 183, Bug 177)
- Supera: ADR 0041 nella parte di orchestrazione dei passi e di raccolta delle fonti

## Contesto

`docs/architecture.md` §5 prescrive il ciclo decisionale come grafo LangGraph: stato tipizzato, fan-out parallelo
con un nodo per fonte attiva, poi contesto, decisione, rischio, esecuzione, registro e persistenza, con un
checkpointer LangGraph su PostgreSQL per ripresa e debug. ADR 0041 aveva invece scritto il ciclo come sequenza di
chiamate in `RunCycleUseCase`, senza grafo e senza checkpoint, scostandosi dall'architettura senza l'approvazione
del proprietario.

Il proprietario autorizza LangGraph come eccezione architetturale nominale: è un vincolo di campo, non una
tecnologia qualsiasi dietro una porta. CLAUDE.md vieta ad `application` le librerie esterne; l'eccezione va scritta
in CLAUDE.md e nelle verifiche, per nome.

## Decisione

- **Eccezione nominale.** `langgraph` si importa solo in due moduli:
  - `application/flows/cycle_graph.py`: costruisce ed esegue il grafo del ciclo; ogni nodo chiama la porta del
    suo passo, la logica di business resta nei casi d'uso e nel domain;
  - `adapters/outbound/sqlalchemy/cycle_checkpoints.py`: il checkpointer (`PostgresSaver`) sulla stessa base
    PostgreSQL, nella cartella della sua tecnologia.

  Le verifiche: `ARCHITECTURAL_LIBRARIES` in `tests/support/architecture.py` (libreria e moduli ammessi, una
  libreria eccezionale non appartiene a nessuna cartella), il contratto import-linter "Domain e application non
  importano tecnologie" con `langgraph` tra i moduli vietati e la sola riga ignorata di `cycle_graph`, gli esempi
  violante e conforme in `test_architecture_rules.py`. CLAUDE.md lo dichiara in Stack e nella regola delle
  dipendenze.
- **Grafo costruito a ogni ciclo** con i soli nodi delle fonti attive (RF-05.02):
  `START → load_state → source_<nome>… (in parallelo) → compose_context → decide → risk_filter → execute →
  update_ledger → persist → END`. Senza fonti attive `load_state` passa direttamente a `compose_context`.
  I nodi corrispondono ai passi registrati del ciclo (`CycleStep`): lettura dello stato, raccolta delle fonti,
  contesto, decisione dell'agente, controllo del rischio, esecuzione degli ordini, aggiornamento dello stato del
  flusso, registrazione del ciclo.
- **Stato del grafo** `CycleState` (`TypedDict`): stato del flusso, letture e fonti assenti (riduttore
  `operator.add`, scritte in parallelo dai nodi fonte), contesto, decisioni, revisione del rischio, esecuzioni,
  passi compiuti e documenti dei passi (riduttore `operator.add`), costo della chiamata. I valori sono gli oggetti
  del domain e delle porte, validati dai loro tipi.
- **Fonti**: ogni nodo fonte chiede la sua fonte attraverso `ConcurrentCallsPort` con l'attesa del ciclo
  (R1.2.5): una fonte che non risponde in tempo o risponde con un errore tipizzato scrive l'assenza nello stato e
  il ciclo prosegue (RF-04.05). `SourceCollector` non serve più.
- **Errori**: fail fast come prima (R1.2.3, R1.2.4). LangGraph rilancia l'errore del nodo; `RunCycleUseCase`
  cattura `AutotradingError`, legge dall'ultimo checkpoint i passi compiuti e registra il ciclo fallito, mette in
  pausa i flussi per un errore permanente e rilancia.
- **Checkpointer** dietro `CycleCheckpointsPort` di `flows`: apre, per un ciclo, il checkpointer del tenant.
  Il `thread_id` è `<tenant>/<flusso>/<istante previsto>`. Le tabelle di LangGraph nascono da una migrazione
  Alembic con lo schema della versione fissata, e hanno row level security sul prefisso del `thread_id`
  (`app.tenant_id`), impostato dall'adapter a ogni connessione. La verità contabile resta nelle tabelle di
  dominio scritte da `persist`.
- **Ripresa**: invocato su un ciclo che ha già un checkpoint con lavoro non finito, `RunCycleUseCase` riprende
  dall'ultimo nodo compiuto (`graph.invoke(None, config)`); altrimenti parte dall'inizio.
- **Composizione**: le porte di ogni passo si collegano per il tenant del flusso con funzioni di composizione
  nelle cartelle delle loro tecnologie e nei casi d'uso; `bootstrap.py` non ha più classi del ciclo
  (`TenantCyclePorts`, `CycleServices`, `SourcesFromSources`, voci del Bug 177).
- **Versioni fissate**: `langgraph>=1.2` e `langgraph-checkpoint-postgres>=3.0`, bloccate da `uv.lock`.
  `zstandard`, dipendenza di `langsmith` (tracciamento, mai attivo: nessuna variabile `LANGSMITH_*`) senza wheel
  per Python 3.15, è esclusa con `override-dependencies` in `pyproject.toml`; `langsmith` si importa senza.

## Alternative scartate

- **LangGraph dietro un adapter** in una cartella propria: il grafo chiama i passi, cioè casi d'uso e porte; un
  adapter che li riceve orchestra, contro CLAUDE.md. Per questo il proprietario ne fa un'eccezione di
  `application`.
- **Eccezione su tutta `application/flows`**: più larga del necessario; il nome del modulo basta.
- **Stato Pydantic** come in §5: porterebbe `pydantic` in `application`, una seconda libreria fuori dalla
  eccezione nominata.
- **Un solo nodo `source` con `Send`**: §5 vuole un nodo per fonte attiva, col nome della fonte nel grafo.
- **Checkpointer scritto a mano su SQLAlchemy**: duplica `PostgresSaver` [doc] senza vantaggi.
- **Tabelle create da `PostgresSaver.setup()`**: schema fuori da Alembic e senza row level security, contro
  `.claude/rules/tech-sqlalchemy.md`.
- **Serializzazione con pickle**: chi scrive nella base eseguirebbe codice nel worker che ha la chiave privata.

## Conseguenze

- Il ciclo è ispezionabile nodo per nodo (`get_state_history`) e riprende dall'ultimo nodo compiuto.
- I valori nello stato devono essere serializzabili dal serializzatore di LangGraph (dataclass, enum, datetime,
  Decimal, UUID); le prove BDD usano un checkpointer in memoria con lo stesso serializzatore, quindi un tipo non
  serializzabile è un test rosso. Una tupla riletta da un checkpoint torna come lista.
- Il comitato (6.28) e il grafo strategico (6.27) si aggiungeranno come sottografi nello stesso modulo.

## Scostamenti

- `CycleState` è un `TypedDict` e non un modello Pydantic (vedi alternative): la validazione resta nei tipi del
  domain.
- Nessun nodo `notify`: le notifiche sono passi dei casi d'uso dei nodi (ordini, chiusure, fallimenti; ADR 0092);
  un nodo vuoto non aggiunge nulla.
- La ripresa automatica di un ciclo interrotto dopo un riavvio del worker non è attivata: l'istante previsto è già
  preso (`claim`) e riprendere in ritardo vuol dire inviare ordini in ritardo, una scelta funzionale senza criteri
  nei requisiti; il blocco è registrato sul Bug 183. Il checkpoint resta per debug e la ripresa è disponibile al
  caso d'uso.

## Confronto con le decisioni scritte

| Fonte | Esito |
|-------|-------|
| `docs/architecture.md:18` (orchestrazione con LangGraph) | Conforme |
| `docs/architecture.md:122` (stato Pydantic `CycleState`) | Scostamento: `TypedDict`, motivato sopra |
| `docs/architecture.md:124-131` (fan-out, un nodo per fonte attiva, riduttore `operator.add`) | Conforme |
| `docs/architecture.md:133` (grafo costruito con le sole fonti attive; fonte fallita = errore nello stato) | Conforme |
| `docs/architecture.md:137` (checkpointer su PostgreSQL per ripresa e debug) | Conforme; ripresa dopo riavvio non attivata, vedi scostamenti |
| `docs/architecture.md:310` (versioni fissate, uso isolato) | Conforme: due moduli nominati, `uv.lock` |
| `CLAUDE.md` regola delle dipendenze (`application` solo domain e libreria standard) | Eccezione nominale del proprietario, scritta in CLAUDE.md |
| `.claude/rules/tech-sqlalchemy.md` (schema da Alembic, RLS per tenant) | Conforme |
| ADR 0041 (ciclo come sequenza di chiamate) | Superata nella parte di orchestrazione |
