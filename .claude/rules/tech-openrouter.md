---
paths:
  - "src/autotrading/adapters/outbound/openrouter/**"
  - "tests/unit/adapters/openrouter/**"
  - "tests/integration/providers/test_openrouter_live.py"
---

# Adapter in uscita: OpenRouter

- API pubblica di OpenRouter (`https://openrouter.ai/api/v1`), raggiunta con `httpx` (libreria di trasporto). Nessun
  SDK di un altro sistema: l'SDK `openai` appartiene a `litellm/`.
- `OpenRouterModelGatewayAdapter` è la fabbrica concreta di `ModelGatewayPort` (abstract factory, ADR 0109): crea
  `OpenRouterModelCallAdapter` (`ModelCallPort`) e `OpenRouterModelCatalogAdapter` (`ModelCatalogPort` di `agent`,
  `FlowModelsPort` di `flows`). Non riceve porte: crea solo oggetti della propria tecnologia.
- **Chiave dell'utente solo nella chiamata del suo flusso** (RF-01.05): intestazione `Authorization` di quella
  richiesta. Gli errori di `httpx` portano la richiesta e si rilanciano senza causa; un messaggio che ripete la
  chiave la maschera (`ProviderKey.redact`).
- **Catalogo dall'elenco pubblico** (`GET /models`, senza chiave): ogni modello che risponde in testo, col nome
  `openrouter/<id>`, temperatura 0-2 se supportata, lunghezza massima dal fornitore principale (o dal contesto),
  livello di ragionamento se supporta `reasoning`, prezzi per milione di token. Nessun modello scritto a mano. Una voce
  in un'altra forma si salta; l'elenco si rilegge ogni 5 minuti.
- **Richiesta**: parametri dell'API compatibile OpenAI più il campo `reasoning` di OpenRouter; `response_format` JSON
  sempre (OpenRouter ignora un parametro che il modello instradato non accetta). Il costo riportato da OpenRouter in
  `usage.cost` è il costo della chiamata (R1.4.6).
- **Errori** (R1.2.3, R1.2.4): 401 e 403 chiave rifiutata, 402 credito esaurito (permanenti); tempo scaduto, rete,
  altri stati e risposta inattesa transitori. Il nuovo tentativo è il ciclo successivo.
- `composition.py` espone `openrouter_adapters()`; `configuration.py` la dataclass privata `_OpenRouterSettings` (solo
  il tempo di attesa: nessun indirizzo né chiave della piattaforma).
- Test di integrazione `-m providers`: elenco pubblico vero e chiave inventata rifiutata, nessuna spesa.
