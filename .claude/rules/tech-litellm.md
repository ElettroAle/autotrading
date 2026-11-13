---
paths:
  - "src/autotrading/adapters/outbound/litellm/**"
  - "tests/unit/adapters/litellm/**"
  - "deploy/litellm/**"
---

# Adapter in uscita: LiteLLM

- Proxy LiteLLM dell'installazione (`http://litellm:4000`, rete interna del compose, nessuna porta pubblicata),
  raggiunto con l'SDK `openai` (`base_url` del proxy, `max_retries=0`). `openai` si importa solo qui; nessun
  adapter per fornitore (ADR 0101).
- **Chiave dell'utente solo nella richiesta del suo flusso** (RF-01.05, ADR 0029): viaggia nel corpo della richiesta
  e il proxy la usa solo per quella. Nel proxy nessuna chiave dei fornitori e nessuna chiave virtuale. La chiave non
  compare in log, errori, `repr` né nella causa di un errore: gli errori dell'SDK portano la richiesta e si
  rilanciano senza causa.
- `LiteLlmModelGatewayAdapter` è la fabbrica concreta di `ModelGatewayPort` (abstract factory, ADR 0109): crea
  `LiteLlmModelCallAdapter` (`ModelCallPort`) e `LiteLlmModelCatalogAdapter` (`ModelCatalogPort` di `agent`,
  `FlowModelsPort` di `flows`, ADR 0103). Serve tutti i fornitori tranne OpenRouter, che ha la sua cartella.
- **Nessun ramo per fornitore** (decisione del proprietario, ADR 0109): la richiesta usa i soli parametri dell'API
  OpenAI (`temperature`, `max_tokens`, `response_format`, `reasoning_effort`); traduzione e `drop_params` sono di
  LiteLLM. Un intervallo unico di temperatura (0-2): un fornitore che accetta meno rifiuta la chiamata col suo motivo.
- **Errori** (R1.2.3, R1.2.4): chiave rifiutata (401, 403) e credito esaurito sono permanenti; tempo scaduto, rete,
  risposta inattesa, chiave master sconosciuta e catalogo non raggiungibile sono transitori. Il nuovo tentativo è il
  ciclo successivo, mai un tentativo del proxy.
- **Catalogo dal proxy, mai scritto a mano**: rotte wildcard per fornitore in `deploy/litellm/config.yaml`, espanse
  con la mappa dei modelli di LiteLLM. Abilitare un fornitore = una rotta. Nessun modello scritto a mano.
- Il proxy gira senza database: il costo di ogni chiamata si registra nel ciclo del flusso (R1.4.6).
- `composition.py` espone `litellm_adapters(source)`; `configuration.py` la dataclass privata `_LiteLlmSettings`
  (indirizzo del proxy e chiave master). La chiave master è generata sulla macchina e letta da file montato in sola
  lettura. **Mai variabili d'ambiente per i segreti.**
