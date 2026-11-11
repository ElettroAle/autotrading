# ADR 0030 — Catalogo dei modelli IA: file JSON di configurazione, parametri validati nel domain

- Stato: accettata (11 novembre 2026)
- Requisiti: R1.4.2 (Task T1.4.2.1)

## Contesto

R1.4.2 chiede un catalogo dei modelli con fornitore, nome e parametri ammessi (valore predefinito e valori
ammessi: temperatura, limite di lunghezza della risposta, livello di ragionamento se il modello lo supporta),
e per ogni fornitore l'indicazione della chiave registrata. Un modello si aggiunge con la sola configurazione.
Un parametro fuori dai valori ammessi, o non supportato dal modello, rende la configurazione del flusso non
valida.

## Decisione

- **Domain di `agent`**: `RangeParameter` (minimo, massimo e predefinito decimali, con l'opzione dei soli
  interi) e `ChoiceParameter` (valori ammessi e predefinito). Ogni parametro ha una chiave della piattaforma
  (`temperature`, `max_tokens`, `reasoning_effort`) e un'etichetta italiana, usata nei motivi di rifiuto.
- `ModelDefinition` ha un nome nella forma di LiteLLM (`<fornitore>/<modello>`), dal quale deriva il
  fornitore, e i suoi parametri. `settings(requested)` risolve i parametri di un flusso: applica i
  predefiniti, e rifiuta con "parametro fuori dai valori ammessi: <etichetta>", "parametro non supportato dal
  modello: <etichetta>" o "parametro sconosciuto: <chiave>". La userà la validazione del flusso (R1.1.1).
- `ModelCatalog` trova un modello per nome (`ModelNotAvailableError`, 404) ed elenca i fornitori.
- **File `models.json`** nel pacchetto dell'adapter `adapters/outbound/json/`, letto all'avvio da
  `load_model_catalog` e composto in `bootstrap.py` (`MODEL_CATALOG`). Un file malformato ferma l'avvio
  (`InvalidModelCatalogError`). Aggiungere un modello vuol dire aggiungere un oggetto al file.
- **Casi d'uso** `ListModelsUseCase` (modelli e fornitori, ognuno con l'indicazione della chiave registrata
  dal tenant); **API** `GET /models`.
- **Catalogo iniziale**: fornitori `anthropic`, `openai`, `deepseek`, `openrouter`, con pochi modelli ciascuno.
  Il costo stimato per ciclo è fuori ambito (R1.4.2), mentre i prezzi arrivano con R1.4.6.

## Alternative scartate

- **Definizioni in Python come per le fonti (ADR 0028)**: una fonte porta con sé il codice che la raccoglie,
  mentre un modello è solo un nome e dei limiti. Il requisito chiede la sola configurazione.
- **Catalogo letto da LiteLLM** (`/model/info`): con le chiavi degli utenti il proxy non elenca modelli propri.
  I limiti dei parametri sono una scelta della piattaforma, non del proxy.
- **Catalogo in database**: nessuna funzione di modifica è richiesta, e un file versionato nel repository si
  rivede in PR.

## Conseguenze

- Un modello nuovo di un fornitore nuovo richiede anche l'endpoint di verifica della chiave (ADR 0029).
- La rule `tech-json.md` descrive l'adapter.
