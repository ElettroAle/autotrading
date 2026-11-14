---
paths:
  - "src/autotrading/adapters/outbound/worker/**"
  - "tests/unit/adapters/worker/**"
---

# Adapter in uscita: API interna del worker

- Client dell'API interna del `worker` usati dall'`api` (ADR 0021), raggiunta con `httpx`, libreria di
  trasporto condivisa. Il contratto lato server è `adapters/inbound/api/worker.py`.
- Ogni chiamata porta il token di servizio come `Authorization: Bearer`, letto da file montato in sola
  lettura; ha un timeout esplicito dichiarato nel modulo.
- Gli adapter (`WorkerAccountStateAdapter`, `WorkerAccountActivityAdapter`, `WorkerPositionClosingAdapter`,
  `WorkerVerificationAdapter`, `WorkerBotIdentityAdapter`, `WorkerNotificationAdapter`,
  `WorkerModelCatalogAdapter`) sono legati al tenant della richiesta quando il dato è del tenant e realizzano
  porte dei contesti consumatori.
- `WorkerModelCatalogAdapter` legge `GET /internal/model-catalog`, fuori dal tenant, e realizza `ModelCatalogPort` e
  `FlowModelsPort` al posto del catalogo LiteLLM, che vive solo nel `worker` (ADR 0148, ADR 0149); lo offre col
  nome `litellm` e conserva la lettura per 5 minuti. Worker non raggiungibile o forma inattesa: catalogo non
  disponibile (503).
- Il worker non raggiungibile o uno stato inatteso si traduce nell'errore del contratto della porta; una
  notifica non consegnata si registra e non fa fallire il chiamante (R1.8.2).
- Il token non compare in log, errori o repr. Nessun import da altre cartelle di adapter.
- `composition.py` espone `worker_adapters(url, token)`: un client per l'installazione e, per ogni
  richiesta, gli adapter legati al tenant; `worker_model_catalog_adapters(source)` il catalogo dei modelli del
  `worker`; `configuration.py` la dataclass privata `_WorkerSettings`.
