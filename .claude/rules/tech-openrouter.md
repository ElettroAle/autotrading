---
paths:
  - "src/autotrading/adapters/outbound/openrouter/**"
  - "tests/unit/adapters/openrouter/**"
  - "tests/integration/providers/test_openrouter_live.py"
---

# Adapter in uscita: OpenRouter

- API pubblica di OpenRouter (`https://openrouter.ai/api/v1`), raggiunta con `httpx` (libreria di trasporto). Nessuna
  libreria di un altro sistema: `litellm` appartiene a `litellm/`.
- `OpenRouterModelGatewayAdapter` è la fabbrica concreta di `ModelGatewayPort` (abstract factory, ADR 0109): crea
  `OpenRouterModelCallAdapter` (`ModelCallPort`) e `OpenRouterModelCatalogAdapter` (`ModelCatalogPort` di `agent`,
  `FlowModelsPort` di `flows`). Non riceve porte: crea solo oggetti della propria tecnologia.
- **Chiave dell'utente solo nella chiamata del suo flusso** (RF-01.05): intestazione `Authorization` di quella
  richiesta. Gli errori di `httpx` portano la richiesta e si rilanciano senza causa; un messaggio che ripete la
  chiave la maschera (`ProviderKey.redact`).
- **Catalogo dall'elenco pubblico** (`GET /models`, senza chiave): ogni modello che risponde in testo e dichiara
  `structured_outputs` tra i parametri supportati (senza non potrebbe rispondere nel formato chiesto), col nome
  `openrouter/<id>`, temperatura 0-2 se supportata, lunghezza massima dal fornitore principale (o dal contesto),
  livello di ragionamento se supporta `reasoning`, prezzi per milione di token. Nessun modello scritto a mano. Una voce
  in un'altra forma si salta; l'elenco si rilegge ogni 5 minuti.
- **Richiesta**: parametri dell'API compatibile OpenAI più i campi `reasoning` e `provider` di OpenRouter;
  `response_format` `json_schema` rigido (`strict: true`) col formato che il caso d'uso passa e
  `provider.require_parameters: true`, perché OpenRouter altrimenti ignora un parametro che il fornitore instradato non
  accetta (ADR risposta-del-modello-con-schema-rigido). Il costo riportato da OpenRouter in `usage.cost` è il costo
  della chiamata (R1.4.6).
- **Errori** (R1.2.3, R1.2.4): 401 e 403 chiave rifiutata, 402 credito esaurito (permanenti); tempo scaduto, rete e
  altri stati transitori. L'errore che OpenRouter mette nel corpo di una risposta 200 (`error` con `message`) è il motivo:
  con un `code` numerico passa dalla stessa traduzione degli stati HTTP, altrimenti è transitorio col suo messaggio; il
  costo, se `usage` c'è, resta (ADR errore-di-openrouter-nella-risposta). Una risposta che non si legge è transitoria.
  L'adapter non ritenta: gli errori transitori li ritenta nel ciclo il caso d'uso, fino a 3 volte con attese di 2, 8 e
  30 secondi (R1.4.9, ADR ritentativo-del-modello-nel-ciclo, ADR tentativi-del-modello-registrati-nel-ciclo).
- `composition.py` espone `openrouter_adapters()`; `configuration.py` la dataclass privata `_OpenRouterSettings` (solo
  il tempo di attesa: nessun indirizzo né chiave della piattaforma).
- Test di integrazione (marker `integration`, nella pipeline a ogni PR): elenco pubblico vero e chiave inventata
  rifiutata, nessuna spesa.
