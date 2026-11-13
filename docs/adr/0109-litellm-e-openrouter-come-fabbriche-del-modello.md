# ADR 0109 — LiteLLM e OpenRouter come due fabbriche della chiamata al modello

- Stato: accettata (13 novembre 2026), decisione del proprietario
- Requisiti: R1.4.1, R1.4.2, R1.4.3, R1.4.6, R1.2.3, R1.2.4, RF-01.05; Bug B1.0.6 (187), Bug B1.4.2 (181)
- Supera: le parti dell'ADR 0101 sui campi per fornitore della richiesta (`OWN_EFFORT_FIELDS`, `JSON_PROVIDERS`) e
  sull'instradamento di OpenRouter nel proxy; le parti dell'ADR 0103 sugli intervalli di temperatura per fornitore e
  sui modelli OpenRouter scritti a mano in `deploy/litellm/config.yaml`
- Collegate: ADR 0101, ADR 0103, ADR 0029 (chiavi dei fornitori dell'utente), ADR 0105 (scelta per nome come gli
  exchange del conto)

## Contesto e problema

Con il proxy LiteLLM integrato (ADR 0101, 0103) l'adapter `litellm/` conteneva ancora logica per fornitore: un campo
del ragionamento diverso per Anthropic e OpenRouter, il formato JSON della risposta solo per OpenAI e DeepSeek, un
intervallo di temperatura diverso per Anthropic, il costo riportato pensato per OpenRouter. In più OpenRouter, che la
mappa dei modelli di LiteLLM non descrive, aveva i modelli scritti a mano nella configurazione del proxy.

Il proprietario ha deciso (13 novembre 2026), in tre passi riportati qui per intero:

- «Se usi LiteLLM non voglio vedere altre implementazioni per altri fornitori. Al massimo, facciamo implementazione
  per OpenRouter»;
- dopo due proposte intermedie (adapter separato scelto per flusso, poi decorator della chiamata), la decisione
  finale: «Open router e Lite LLM separati. Dipende dalla config che si chiede al flusso. Usa un abstract factory».

## Decisione

- **Abstract factory.** `application/agent/ports.py` dichiara `ModelGatewayPort`, la fabbrica astratta di una
  famiglia coerente di prodotti: `model_call() -> ModelCallPort` e `model_catalog() -> ModelCatalogPort`.
- **Due fabbriche concrete, due cartelle indipendenti.**
  - `adapters/outbound/litellm/`: `LiteLlmModelGatewayAdapter` crea `LiteLlmModelCallAdapter` e
    `LiteLlmModelCatalogAdapter`. Serve tutti i fornitori con una rotta nel proxy, **senza alcun ramo per
    fornitore**: la richiesta usa solo i parametri dell'API OpenAI (`temperature`, `max_tokens`, `response_format`,
    `reasoning_effort`), traduzione e `drop_params` sono di LiteLLM; la temperatura ha un solo intervallo (0-2).
  - `adapters/outbound/openrouter/`: `OpenRouterModelGatewayAdapter` crea `OpenRouterModelCallAdapter` (chiamata
    diretta all'API di OpenRouter con `httpx`, chiave dell'utente nell'intestazione della sola chiamata, campo
    `reasoning`, costo riportato in `usage.cost`) e `OpenRouterModelCatalogAdapter` (elenco pubblico
    `GET /api/v1/models`, senza chiave: nessun modello scritto a mano).
  - Ogni fabbrica crea solo oggetti della propria tecnologia e non riceve porte; i prodotti sono creati una volta e
    restituiti sempre gli stessi (il catalogo conserva la sua lettura per 5 minuti).
- **La scelta della fabbrica la fa il caso d'uso, dalla configurazione del flusso.** I casi d'uso ricevono da
  `bootstrap.py` le fabbriche per nome, come scelgono l'exchange del conto per nome. Il gateway non è un campo nuovo
  del flusso: si deriva dal modello che il flusso ha scelto, cercandolo nei cataloghi delle fabbriche; la fabbrica il
  cui catalogo contiene il modello è quella che lo chiama. Il catalogo mostrato all'utente unisce i cataloghi delle
  fabbriche nel caso d'uso. `bootstrap.py` istanzia e collega, senza decisioni.
- **Proxy.** La rotta `openrouter/*` e il modello scritto a mano escono da `deploy/litellm/config.yaml`.
- **Rule e test.** `.claude/rules/tech-openrouter.md`, voce nell'indice di `CLAUDE.md`, `httpx` dichiarata per la
  cartella in `TECHNOLOGY_LIBRARIES`, cartella nel contratto di indipendenza di import-linter. Test di integrazione
  `-m providers` sull'elenco pubblico vero e con una chiave inventata: nessuna spesa.

## Alternative scartate

- **Un solo adapter `litellm/` con rami per fornitore** (stato precedente): contro la decisione del proprietario.
- **OpenRouter instradato dal proxy con `check_provider_endpoint`** (LiteLLM ≥ 1.110): la scoperta dei modelli usa la
  chiave della rotta o una variabile d'ambiente; senza chiavi della piattaforma (RF-01.05) la rotta non aggiunge nulla,
  e una chiave in variabile d'ambiente è vietata.
- **Decorator della chiamata e del catalogo LiteLLM** (proposta intermedia del proprietario, poi sostituita): il
  decorator non può cambiare la richiesta che l'adapter interno costruisce attraverso la sola porta, e avrebbe
  lasciato OpenRouter dipendente dal proxy. Sostituito dalla decisione finale.
- **Adapter OpenRouter scelto da un adapter che orchestra, o da `bootstrap.py`**: contro CLAUDE.md (il caso d'uso
  orchestra; `bootstrap.py` senza decisioni).
- **Campo «gateway» nella configurazione del flusso**: richiederebbe una migrazione e un requisito nuovo, mentre il
  modello scelto basta a individuare la fabbrica.
- **SDK `openai` anche per OpenRouter**: l'SDK appartiene alla cartella `litellm/` (una libreria di sistema in una sola
  cartella); `httpx` è la libreria di trasporto che più cartelle possono usare.

## Confronto con le decisioni scritte

| Fonte | Esito |
|---|---|
| `CLAUDE.md` «Regola delle dipendenze» (un adapter = una tecnologia; cartelle indipendenti; nessuna porta nel costruttore) | conforme: due cartelle, fabbriche che creano solo prodotti propri |
| `CLAUDE.md` «Il caso d'uso orchestra gli adapter» e `bootstrap.py` come Program.cs | conforme: la scelta della fabbrica è nel caso d'uso |
| `docs/architecture.md` §LiteLLM (proxy per i modelli) | scostamento dichiarato: OpenRouter non passa dal proxy, per decisione del proprietario |
| `docs/requirements.md` RF-01.05 (chiavi dell'utente solo per i suoi flussi) | conforme: chiave nella sola richiesta del flusso, in entrambe le fabbriche |
| R1.4.2 (catalogo senza modelli scritti a mano, parametri ammessi) | conforme: entrambi i cataloghi letti da fonti vive |
| R1.4.6 (costo per chiamata) | conforme: costo riportato se presente, altrimenti i prezzi del catalogo |

## Scostamenti

- `docs/architecture.md` descrive LiteLLM come unico accesso ai modelli: OpenRouter ora è chiamato direttamente.
  Decisione del proprietario; il testo di `architecture.md` va allineato.
- Intervallo di temperatura unico (0-2) anche per i fornitori che accettano meno (Anthropic accetta 0-1): un valore
  sopra 1 su un modello Anthropic è accettato alla creazione del flusso e rifiutato dal fornitore alla chiamata, come
  errore transitorio con il motivo del fornitore. Conseguenza diretta del «nessun ramo per fornitore».
- Il livello di ragionamento passa a LiteLLM come `reasoning_effort` per ogni fornitore: per un modello Anthropic che
  LiteLLM non conosce la traduzione è quella di LiteLLM.

## Conseguenze

- Un fornitore nuovo nel proxy è una rotta, senza codice; un modello nuovo di OpenRouter compare da solo.
- Un'indisponibilità dell'elenco di OpenRouter non ferma i flussi che usano modelli del proxy, e viceversa.
- Il decorator non ha effetti collaterali e non c'è: l'outbox (Task 178) non riguarda questo lavoro.
