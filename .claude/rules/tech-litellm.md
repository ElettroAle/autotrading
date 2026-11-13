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
- `LiteLlmModelCallAdapter` realizza `ModelCallPort`; `LiteLlmModelCatalogAdapter` realizza le porte del catalogo dei
  contesti che lo usano (`ModelCatalogPort` di `agent`, `FlowModelsPort` di `flows`), leggendo il proxy (ADR 0103).
- **Errori** (R1.2.3, R1.2.4): chiave rifiutata (401, 403) e credito esaurito sono permanenti; tempo scaduto, rete,
  risposta inattesa, chiave master sconosciuta e catalogo non raggiungibile sono transitori. Il nuovo tentativo è il
  ciclo successivo, mai un tentativo del proxy.
- **Catalogo dal proxy, mai scritto a mano**: rotte wildcard per fornitore in `deploy/litellm/config.yaml`, espanse
  con la mappa dei modelli di LiteLLM. Abilitare un fornitore = una rotta (ADR 0103, ADR 0108);
  unica eccezione i modelli OpenRouter, che la mappa non descrive.
- Il proxy gira senza database: il costo di ogni chiamata si registra nel ciclo del flusso (R1.4.6).
- `composition.py` espone `litellm_adapters(source)`; `configuration.py` la dataclass privata `_LiteLlmSettings`
  (indirizzo del proxy e chiave master). La chiave master è generata sulla macchina e letta da file montato in sola
  lettura. **Mai variabili d'ambiente per i segreti.**
