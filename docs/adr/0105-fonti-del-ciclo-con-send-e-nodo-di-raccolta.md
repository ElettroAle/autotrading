# ADR 0105 Fonti del ciclo con Send e nodo di raccolta

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.2.1, R1.2.5 (Bug 183)
- Supera: ADR 0104 nei punti "grafo costruito a ogni ciclo con i soli nodi delle fonti attive" e nell'alternativa
  scartata "un solo nodo `source` con `Send`"

## Contesto

ADR 0104 voleva un nodo per fonte attiva, con il grafo costruito a ogni ciclo. Le fonti attive però si conoscono
solo dopo `load_state`, che legge la configurazione del flusso dentro il grafo: costruire il grafo prima vorrebbe
dire leggere il flusso fuori dal grafo, e la ripresa da un checkpoint non avrebbe più il primo nodo. Inoltre il
passo registrato "raccolta dei dati delle fonti" deve risultare compiuto prima del contesto anche quando il
contesto fallisce (R1.2.1, R1.2.3).

## Decisione

- Il grafo è lo stesso per ogni ciclo. Dopo `load_state` un arco condizionale manda, con `Send`, un compito del
  nodo `source` per ogni fonte attiva dello stato del flusso, tutti nello stesso passo e quindi in parallelo; ogni
  compito porta il nome della sua fonte. Senza fonti attive l'arco porta direttamente al nodo di raccolta.
- Un nodo `collect_sources` riunisce i compiti delle fonti e registra il passo "raccolta dei dati delle fonti" con
  le letture; poi `compose_context`.
- Il passo fallito di un ciclo è il primo passo non compiuto nello stato dopo l'ultimo nodo concluso, che il grafo
  restituisce in streaming (`stream_mode="values"`).
- Il valore nello stato deve essere serializzabile dal serializzatore di LangGraph: le mappe immutabili del domain
  (`FlowState.expected_positions`, `FlowTotals.positions`) passano da `MappingProxyType` a `frozendict` (PEP 814,
  Python 3.15), che il serializzatore conosce; il comportamento non cambia.

## Alternative scartate

- **Leggere il flusso fuori dal grafo per costruirlo con i soli nodi attivi**: `load_state` non sarebbe più un
  nodo, la ripresa ripartirebbe senza lo stato letto.
- **Tutti i nodi delle fonti del catalogo, attivati da un arco condizionale**: il contesto `flows` dovrebbe
  conoscere il catalogo delle fonti, che è di `sources`.
- **Registrare la raccolta nel nodo del contesto**: se il contesto fallisce, la raccolta non risulterebbe compiuta.
- **Serializzazione con pickle per i tipi non noti**: ADR 0104, esclusa.

## Conseguenze

- In ogni ciclo partono solo le fonti attive, come voleva §5; nel grafo compaiono come compiti del nodo `source`.
- Un tipo nuovo nello stato che il serializzatore non conosce rompe le prove BDD, che usano un checkpointer in
  memoria con lo stesso serializzatore.

## Confronto con le decisioni scritte

| Fonte | Esito |
|-------|-------|
| `docs/architecture.md:124-131` (fan-out parallelo, un nodo per fonte attiva, riduttore `operator.add`) | Conforme nella sostanza: un compito per fonte attiva, in parallelo, riduttore `operator.add` |
| `docs/architecture.md:133` (grafo con le sole fonti attive; fonte fallita = errore nello stato, il ciclo prosegue) | Conforme: partono solo le fonti attive; l'assenza va nello stato |
| ADR 0104 | Superata nei due punti indicati |
| `.claude/rules/layer-domain.md` (solo libreria standard) | Conforme: `frozendict` è della libreria standard |
