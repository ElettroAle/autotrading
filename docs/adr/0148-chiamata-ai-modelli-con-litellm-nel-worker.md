# ADR 0148 — Chiamata ai modelli con la libreria LiteLLM nel worker, senza proxy

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: Bug 255 (Task 256); RF-01.05, RF-16
- Collegate: sostituisce ADR 0101; sostituisce le parti sul proxy di ADR 0103 e ADR 0109; ADR 0149 (catalogo dal
  worker); ADR 0150 (installazione senza il container); decisione del proprietario del 14 novembre 2026

## Contesto e problema

LiteLLM gira come proxy in un container proprio (ADR 0101), raggiunto da api e worker con l'SDK OpenAI e una chiave
master generata sulla macchina. Il proxy fa solo da traduttore verso i fornitori e occupa 993 MiB a riposo sulla
macchina dev, più di tutti gli altri servizi insieme. Il proprietario ha chiesto LiteLLM come adapter dentro l'app.

## Fattori decisionali

- Decisione del proprietario (14 novembre 2026): LiteLLM come libreria nell'adapter `litellm/`, nel solo worker.
- `CLAUDE.md`, regola delle dipendenze: una libreria specifica di un sistema appartiene a una sola cartella adapter.
- ADR 0109: LiteLLM e OpenRouter restano due fabbriche della chiamata al modello; nessun codice per fornitore.
- ADR 0007: le chiavi dei fornitori le apre solo il worker.
- Documentazione di LiteLLM: l'SDK per una sola applicazione Python senza chiavi virtuali, spesa o log centralizzati;
  il gateway per più applicazioni.
- Misura locale (Python 3.13): la libreria aggiunge circa 200 MiB per processo, una volta all'import; una chiamata
  aggiunge pochi MiB.

## Opzioni considerate

### 1. Proxy invariato con limiti di memoria

- Pro: nessun cambio di codice.
- Contro: resta il servizio più pesante; contraddice la decisione del proprietario.

### 2. Libreria in api e worker

- Pro: l'api legge il catalogo da sé.
- Contro: circa 200 MiB anche nell'api; versione e fornitori da tenere allineati in due processi.

### 3. Libreria solo nel worker

- Pro: circa 830 MiB in meno rispetto a oggi; la libreria vive dove già si aprono le chiavi e partono le chiamate.
- Contro: l'api deve chiedere il catalogo al worker (ADR 0149).

## Esito della decisione

Opzione 3. L'adapter `adapters/outbound/litellm/`, composto solo da `create_worker_application`, usa
`litellm.completion` con il modello `fornitore/modello` del flusso, la chiave dell'utente solo in quella chiamata
(`api_key`), output strutturato, `drop_params=True`, `num_retries=0` e il timeout dell'adapter. Messaggi e risposte mai
nei log (`turn_off_message_logging`), telemetria spenta, nessuna callback. Gli errori della libreria si traducono
nell'adapter negli errori della porta, come oggi. I fornitori abilitati sono un'impostazione dell'adapter
(`_LiteLlmSettings`, oggi `anthropic`, `deepseek`, `openai`). Il catalogo viene dalla mappa dei modelli della libreria
(`litellm.model_cost`): solo modelli di chat dei fornitori abilitati, nessuna chiamata di rete. L'SDK `openai` esce dal
progetto. `docs/architecture.md` e `.claude/rules/tech-litellm.md` si allineano nella stessa PR.

Verifica: prova (la regola delle librerie dichiara `litellm` solo nella cartella `litellm/`; l'api non compone
`litellm_adapters`).

### Conseguenze

- Il worker passa da circa 156 a circa 360 MiB; il peso si misura dopo il rilascio (Task 253).
- Il catalogo segue la versione della libreria, bloccata in `uv.lock` con gli hash: aggiornarla porta modelli nuovi.
- L'immagine cresce delle dipendenze della libreria.
