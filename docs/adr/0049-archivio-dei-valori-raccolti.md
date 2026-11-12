# ADR 0049 — Archivio dei valori raccolti con istante di riferimento e di raccolta

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.3.8 (Task T1.3.8.1)

## Contesto

R1.3.8 chiede che ogni valore raccolto da una fonte sia registrato con fonte, asset (se la fonte è per asset),
istante di riferimento del dato, istante di raccolta, ciclo e flusso. L'istante di riferimento è quello a cui il
dato si riferisce (chiusura della candela, pubblicazione della notizia, aggiornamento dell'indice). Fuori ambito
il riuso tra flussi e il replay. Un ciclo è identificato dal suo flusso e dall'istante pianificato (ADR 0041).

## Decisione

- **Domain** `SourceValue` (istante di riferimento e valori, come li dà un lettore) e `SourceSample` (il valore
  registrato, con `CycleReference` = flusso e istante pianificato). Ogni istante deve avere il fuso: un valore
  senza è un difetto del lettore (`InvalidSourceSampleError`, 500).
- I valori sono testi per chiave, gli stessi che il contesto dell'agente riceve: il replay rilegge ciò che
  l'agente ha visto.
- **Porta** `SampleRepositoryPort.add(samples)`, legata al tenant del flusso. `CollectSourceUseCase` registra i
  valori di una fonte tutti insieme, dopo che la lettura è riuscita per ogni asset.
- **Adapter** `SqlAlchemySampleRepositoryAdapter` sulla tabella `source_samples` (migrazione `0010`): chiave
  esterna composta verso `flows (id, tenant_id)`, indice per ciclo, row level security per tenant e soli permessi
  di lettura e inserimento: un valore raccolto è un fatto di un ciclo passato, non si modifica né si cancella.

## Alternative scartate

- **Valori dentro la registrazione del ciclo (R1.7.1)**: la registrazione del ciclo dice che cosa è successo; i
  valori servono a replay e analisi per fonte e asset, e una riga per valore si interroga senza aprire documenti.
- **Una tabella per fonte con colonne tipizzate**: ogni fonte nuova del catalogo chiederebbe una migrazione,
  contro R1.3.1 (una fonte aggiunta è selezionabile senza altre modifiche).
- **Identificativo di ciclo generato**: il ciclo è già unico per flusso e istante pianificato.

## Conseguenze

- La tabella cresce con ogni ciclo: la conservazione e la pulizia si decidono quando arriva il replay.
- Il worker registra con l'identità applicativa, impostando il tenant del flusso nella transazione.
