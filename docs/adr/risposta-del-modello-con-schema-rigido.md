# ADR risposta-del-modello-con-schema-rigido — Risposta del modello chiesta con lo schema delle decisioni

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 416 (Task 417), R1.4.5, R1.4.2
- Collegate: ADR 0109 (gateway dei modelli, nessun ramo per fornitore), ADR 0148 (LiteLLM nel worker)

## Contesto e problema

La piattaforma chiede al modello la risposta con `response_format: {"type": "json_object"}`: il fornitore garantisce
solo che il testo sia JSON, non che contenga le decisioni. In dev il ciclo delle 21:50 UTC del 15 novembre 2026 del
flusso `prova-btc` (modello `openrouter/~deepseek/deepseek-flash-latest`) ha ricevuto `{">": {"> ": "decisioni"}}`,
1292 token pagati e scartati come «risposta non leggibile». Le API compatibili OpenAI offrono la modalità
`json_schema` con `strict: true`: il fornitore vincola la generazione allo schema dato.

## Fattori decisionali

- La forma delle decisioni la conosce il domain; adapter e fornitori non la riscrivono.
- Nessun ramo per fornitore in LiteLLM (ADR 0109); OpenRouter è il solo adapter con regole proprie.
- La lettura delle decisioni nel domain resta la validazione finale (R1.4.5): conserva risposta e costo anche quando il
  fornitore tratta lo schema come un suggerimento.
- Un modello che non può rispettare lo schema non deve far fallire i cicli in silenzio.

## Opzioni considerate

### 1. Schema delle decisioni dal domain, passato dal caso d'uso alla porta, `json_schema` rigido negli adapter

- `domain/agent/answer_schema.py` costruisce lo schema JSON rigido dalle stesse chiavi di `AgentResponse`: oggetto con
  `decisioni` obbligatorio, elenco di oggetti con tutti i campi obbligatori, `azione` tra apri/chiudi/mantieni,
  `direzione` long/short o null, `quota` numero o null, `leva` intero o null, `ragionamento` testo,
  `additionalProperties: false` ovunque (la forma che la modalità rigida accetta).
- `ModelCallPort.call` riceve lo schema; `AskAgentUseCase` passa quello delle decisioni.
- OpenRouter: `response_format` `json_schema` rigido e `provider.require_parameters: true`, così OpenRouter instrada
  solo verso fornitori che rispettano il formato. Il catalogo OpenRouter offre solo i modelli che dichiarano
  `structured_outputs` tra i parametri supportati: un modello senza non potrebbe rispondere.
- LiteLLM: `json_schema` rigido quando la libreria dichiara che il modello lo supporta (`supports_response_schema`),
  altrimenti `json_object`. È una capacità che la libreria dichiara per il modello, non un ramo per fornitore. La
  validazione lato client della libreria resta spenta: solleverebbe un errore perdendo risposta e costo, che il domain
  invece conserva.
- Buona: il vincolo agisce dove il token si genera; il domain resta l'unico giudice. Cattiva: una firma della porta in
  più; OpenRouter offre meno modelli (circa 390 su 470 oggi).

### 2. Solo istruzioni più severe nel messaggio di sistema

- Cattiva: resta una richiesta, non un vincolo; il caso reale aveva già lo schema descritto nel messaggio.

### 3. `json_schema` su OpenRouter senza `require_parameters`

- Cattiva: OpenRouter ignora il parametro per i fornitori che non lo accettano e il caso reale si ripete.

### 4. Ritentare il modello quando la risposta non è leggibile

- Cattiva: costo doppio e nessuna garanzia; il nuovo tentativo è il ciclo successivo (R1.2.3).

## Esito della decisione

Opzione 1.

### Conseguenze

- I modelli che garantiscono il formato non possono più rispondere fuori schema; quelli di LiteLLM senza la capacità
  dichiarata restano in `json_object` e la lettura del domain li scarta come oggi.
- Un flusso con un modello OpenRouter che smette di supportare il formato fallisce il ciclo col motivo del fornitore
  (transitorio) e il modello sparisce dal catalogo.
- Le regole `tech-openrouter.md`, `tech-litellm.md` e `context-agent.md` descrivono la richiesta con lo schema.
