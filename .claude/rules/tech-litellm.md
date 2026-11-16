---
paths:
  - "src/autotrading/adapters/outbound/litellm/**"
  - "tests/unit/adapters/litellm/**"
  - "tests/integration/providers/test_model_call_live.py"
---

# Adapter in uscita: LiteLLM

- **Libreria LiteLLM nel solo `worker`** (ADR 0148): nessun proxy, nessun container, nessuna chiave master. `litellm` si
  importa solo qui, con `lazy import`: l'`api` importa i moduli tramite `bootstrap.py` ma non carica mai la libreria
  (circa 200 MiB per processo), la carica il `worker` quando compone il gateway. `litellm_adapters()` la compone solo
  `create_worker_application`; l'`api` chiede il catalogo al `worker` (ADR 0149, `tech-worker.md`). Nessun adapter per
  fornitore.
- **Chiave dell'utente solo nella chiamata del suo flusso** (RF-01.05, ADR 0029): i campi della chiave (`api_key`
  e gli altri che `validate_environment` chiede per il modello, ADR 0159) come parametri di quella sola
  `litellm.completion`. Nessuna chiave dei fornitori della piattaforma. La chiave non compare in log, errori, `repr` né
  nella causa di un errore: gli errori della libreria portano la richiesta e si rilanciano senza causa; un messaggio che
  ripete la chiave la maschera (`ProviderKey.redact`).
- `LiteLlmModelGatewayAdapter` è la fabbrica concreta di `ModelGatewayPort` (abstract factory, ADR 0109): crea
  `LiteLlmModelCallAdapter` (`ModelCallPort`) e `LiteLlmModelCatalogAdapter` (`ModelCatalogPort` di `agent`,
  `FlowModelsPort` di `flows`). Riceve dalla composizione le funzioni della libreria (`completion`,
  `get_supported_openai_params`, `supports_response_schema`) e la mappa dei modelli (`model_cost`). Serve tutti i fornitori abilitati tranne
  OpenRouter, che ha la sua cartella.
- **Nessun ramo per fornitore** (decisione del proprietario, ADR 0109): la chiamata usa i soli parametri dell'API
  OpenAI (`temperature`, `max_tokens`, `response_format`, `reasoning_effort`) con `drop_params=True`, `num_retries=0` e
  il timeout dell'adapter (120 secondi); la traduzione è di LiteLLM. `response_format` è `json_schema` rigido col
  formato che il caso d'uso passa quando la libreria dichiara il modello capace (`supports_response_schema`, una
  capacità del modello, non un ramo per fornitore), altrimenti `json_object`; mai la validazione della libreria, che
  perderebbe risposta e costo (ADR risposta-del-modello-con-schema-rigido). Un intervallo unico di temperatura (0-2): un
  fornitore che accetta meno rifiuta la chiamata col suo motivo.
- **Errori** (R1.2.3, R1.2.4): chiave rifiutata (401, 403) e credito esaurito (402) sono permanenti; un 429, anche con la
  quota esaurita nel messaggio, è transitorio (ADR http-429-mai-permanente); tempo scaduto, rete, ogni altro rifiuto (stato e messaggio originale) e risposta
  inattesa sono transitori. Il nuovo tentativo è il ciclo successivo, mai un tentativo della libreria.
- **Catalogo dalla mappa dei modelli della libreria, mai scritto a mano**: i modelli di chat dei fornitori abilitati,
  col nome `<fornitore>/<modello>` (un modello che la mappa nomina con e senza fornitore si offre una volta),
  temperatura se la libreria la dichiara supportata, lunghezza massima della risposta, livello di ragionamento se
  supportato, prezzi per milione di token. Nessuna chiamata di rete: la mappa è quella della versione bloccata in
  `uv.lock` (`LITELLM_OFFLINE_MODE` nel compose del `worker`) e si legge una volta.
- **Riservatezza**: messaggi e risposte mai nei log della libreria (`turn_off_message_logging`), nessuna callback,
  nessun messaggio di aiuto della libreria nei log.
- Il costo di ogni chiamata si registra nel ciclo del flusso (R1.4.6): i fornitori della libreria non lo riportano, si
  usano i prezzi del catalogo.
- `composition.py` espone `litellm_adapters()`; `configuration.py` la dataclass privata `_LiteLlmSettings` (fornitori
  abilitati, oggi `anthropic`, `deepseek`, `openai`, e tempo di attesa). Abilitare un fornitore è un nome lì.
- Test di integrazione `-m providers`: la libreria chiama ogni fornitore abilitato con una chiave inventata, che il
  fornitore rifiuta, nessuna spesa.
