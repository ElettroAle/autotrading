# ADR 0149 — Catalogo dei modelli LiteLLM chiesto dall'api al worker

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: Bug 255 (Task 266); R1.4.2
- Collegate: ADR 0148 (libreria solo nel worker), ADR 0021 (api e worker sulla rete interna), ADR 0109 (due fabbriche)

## Contesto e problema

Con la libreria solo nel worker (ADR 0148), l'api non può più leggere da sé il catalogo LiteLLM, che le serve per il
catalogo della dashboard (R1.4.2), per riconoscere il fornitore di una chiave e per validare il modello di un flusso.

## Fattori decisionali

- ADR 0021: l'api parla col worker sulla rete interna con il token di servizio, tramite l'adapter `worker/`.
- `CLAUDE.md`: un adapter = una tecnologia; il contesto che usa un dato dichiara le sue porte; niente ponti.
- ADR 0027: l'errore dichiara la propria risposta.

## Opzioni considerate

### 1. Endpoint del worker letto dall'adapter `worker/` dell'api

- Pro: canale, autenticazione e adapter esistono già; nessuna tecnologia nuova.
- Contro: con il worker fermo il catalogo LiteLLM non c'è.

### 2. Copia del catalogo nel database scritta dal worker

- Pro: l'api lo legge anche col worker fermo.
- Contro: tabella e sincronizzazione nuove per dati che cambiano solo con la versione della libreria.

## Esito della decisione

Opzione 1. Il worker espone `GET /internal/model-catalog` (fuori dal tenant: il catalogo è uguale per tutti) che
restituisce modelli e parametri del suo adapter `litellm/`. Nell'api, il nuovo `WorkerModelCatalogAdapter` in
`adapters/outbound/worker/` realizza le porte del catalogo (`ModelCatalogPort`, `FlowModelsPort`) al posto del catalogo
del proxy, sotto lo stesso nome `litellm` nella mappa delle fabbriche. I casi d'uso dell'api che oggi ricevono le
fabbriche intere per leggere solo il catalogo ricevono i soli cataloghi. Worker non raggiungibile o risposta in forma
inattesa: l'errore del catalogo non disponibile già dichiarato dalla porta (503); i modelli OpenRouter restano
disponibili come oggi. La dashboard non cambia.

Verifica: revisione.

### Conseguenze

- Il catalogo LiteLLM dipende dal worker acceso; senza worker non gira comunque nessun ciclo.
