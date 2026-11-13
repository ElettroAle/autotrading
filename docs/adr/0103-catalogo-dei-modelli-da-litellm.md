# ADR 0103 — Catalogo dei modelli descritto dal proxy LiteLLM

- Stato: accettata (13 novembre 2026), decisione del proprietario; gli scostamenti elencati sotto sono di dettaglio
- Requisiti: R1.4.2, R1.4.6, R1.1.1; Bug B1.4.2 (181)
- Supera: ADR 0030 (catalogo scritto a mano in `adapters/outbound/json/models.json`)
- Collegate: ADR 0101 (chiamata ai modelli tramite il proxy LiteLLM), ADR 0029 (chiavi dei fornitori dell'utente)

## Contesto e problema

L'ADR 0030 teneva il catalogo dei modelli in un file JSON scritto a mano: sei modelli, con i loro limiti, da
aggiornare a ogni modello nuovo di un fornitore. Scartava il catalogo letto da LiteLLM perché, con le chiavi degli
utenti, il proxy non avrebbe modelli propri. Con l'ADR 0101 il proxy è in funzione e ha una rotta wildcard per
fornitore: provato in locale (LiteLLM 1.83.14), `GET /model_group/info` espande ogni rotta wildcard nei modelli che
la mappa dei modelli di LiteLLM conosce per quel fornitore, con tipo (`mode`), massimo di token di risposta,
prezzi per token, supporto del ragionamento e parametri OpenAI accettati. Nessuna chiave serve per leggerli.

Il proprietario ha deciso: il catalogo non si tiene a mano, viene da LiteLLM; la chiave non fa parte del catalogo;
abilitare un fornitore è una riga di configurazione; `models.json` e il suo adapter si eliminano.

## Decisione

- **Porte del consumatore.** `agent` dichiara `ModelCatalogPort.catalog() -> ModelCatalog` (errore
  `ModelCatalogUnavailableError`, 503, transitorio); `flows` dichiara `FlowModelsPort.definition_of(model)` con i suoi
  errori (`ModelNotAvailableError`, `FlowModelCatalogUnavailableError`, 503). `ListModelsUseCase`,
  `AskAgentUseCase`, la registrazione delle chiavi e `SelectModelUseCase` le ricevono al posto del catalogo fisso.
- **Adapter `LiteLlmModelCatalogAdapter`** in `adapters/outbound/litellm/`, stessa tecnologia della chiamata: le
  realizza entrambe leggendo `/model_group/info` con la chiave master (SDK `openai`, 10 secondi). Il catalogo letto
  si tiene per 5 minuti: il proxy impara le sue rotte all'avvio, quindi una lettura per richiesta non vedrebbe nulla
  di nuovo.
- **Quali modelli.** Solo nomi `<fornitore>/<modello>` senza `*`, `mode` uguale a `chat` e massimo di token di
  risposta noto. Una voce di forma diversa si salta, le altre restano selezionabili.
- **Parametri** (i nomi e le scelte sono quelli dell'ADR 0030, invariati per l'utente):
  - `temperature` se il modello la accetta (`supported_openai_params`): da 0 a 1 per Anthropic, da 0 a 2 per gli
    altri, predefinita 1;
  - `max_tokens` intero da 1 al massimo del modello, predefinito 4096 o il massimo se minore;
  - `reasoning_effort` (basso, medio, alto; predefinito medio) se il modello supporta il ragionamento.
- **Prezzi**: costo per token della mappa di LiteLLM per un milione; nessun prezzo se manca o se entrambi valgono
  zero (le rotte wildcard non hanno prezzo). Servono solo quando il fornitore non dichiara il costo (R1.4.6).
- **OpenRouter**: la mappa di LiteLLM non lo descrive, la sua rotta wildcard non si espande. I suoi modelli entrano
  nel catalogo scritti in `deploy/litellm/config.yaml` con `model_info` (`mode: chat`, `max_output_tokens`): oggi
  `openrouter/deepseek/deepseek-chat`, come nel catalogo precedente.
- **Composizione**: `bootstrap.py` costruisce l'adapter con `litellm_model_catalog(url, chiave master)` e lo passa
  sia ad `agent` sia a `flows`, nell'`api` e nel `worker`.
- Eliminati `adapters/outbound/json/model_catalog.py`, `models.json` e i loro test. I test usano
  `InMemoryModelCatalogAdapter` (`tests/fakes/`) sul catalogo di prova `tests/support/model_catalog.py`, con gli
  stessi sei modelli di prima.
- La prova dal vivo (marcatore `providers`) legge il catalogo dal proxy e manda una chiave inventata a un modello
  per fornitore: ogni fornitore la rifiuta, senza consumare credito.

## Alternative scartate

- **Tenere `models.json`**: esclusa dal proprietario; ogni modello nuovo richiedeva una PR.
- **`/model/info`**: elenca le rotte così come sono scritte, senza espandere le wildcard.
- **Leggere la mappa dei modelli di LiteLLM (`model_cost`) nell'adapter**: richiederebbe la libreria `litellm` nel
  servizio e duplicherebbe ciò che il proxy già espone.
- **Lettura a ogni richiesta**: nessun vantaggio (il proxy cambia solo al riavvio) e una chiamata in più per ogni
  validazione di un flusso.

## Confronto con le decisioni scritte

- `docs/architecture.md` (catalogo dei modelli da LiteLLM): rispettata.
- `docs/requirements.md` RF-01.05 e ADR 0029: la chiave non serve per il catalogo e non viaggia con la sua lettura.
- R1.4.2: catalogo con fornitore, nome, parametri ammessi e predefiniti, chiave registrata per fornitore; un modello
  si aggiunge con la sola configurazione (anzi, i modelli di un fornitore abilitato arrivano da soli).
- CLAUDE.md: porte nel `ports.py` del contesto che le usa, adapter senza porte né casi d'uso, nessun ponte tra
  contesti (un adapter realizza la porta di `agent` e quella di `flows`), `bootstrap.py` istanzia e collega.

## Scostamenti

1. **Limiti della temperatura per fornitore nell'adapter**: LiteLLM dice se un modello accetta la temperatura, non
   il suo intervallo. L'intervallo è quello dell'API del fornitore (Anthropic 0-1, gli altri 0-2).
2. **Predefiniti della piattaforma** (4096 token, ragionamento medio, temperatura 1): LiteLLM non li conosce; sono
   quelli dell'ADR 0030.
3. **OpenRouter scritto nella configurazione del proxy**: la sola eccezione al catalogo senza elenchi, perché la
   mappa di LiteLLM non lo descrive.
4. **Un fornitore nuovo richiede ancora il controllo della sua chiave** (ADR 0029, ADR 0101 scostamento 3): un test
   confronta le rotte della configurazione con le verifiche disponibili.

## Conseguenze

- Il catalogo segue LiteLLM: un aggiornamento dell'immagine del proxy porta modelli nuovi e toglie quelli ritirati.
  Un flusso che usa un modello sparito dal catalogo non supera più la validazione della configurazione e il suo
  ciclo fallisce con «modello non disponibile», come prima per un modello tolto dal file.
- `api` e `worker` leggono il catalogo dal proxy: se il proxy è giù l'elenco dei modelli e la validazione del modello
  di un flusso rispondono 503, il ciclo è transitorio. L'avvio dei servizi non dipende dal proxy.
- La rule `tech-json.md` non descrive più il catalogo; `context-agent.md` rimanda a questa ADR.
