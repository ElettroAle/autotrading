# ADR 0099 — Revisione AI obbligatoria delle pull request

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.5.1 (Task T0.5.6)
- Collegate: ADR 0004 (controlli di qualità bloccanti), ADR 0084 (collegamento delle PR ai work item)

## Contesto e problema

Molte regole di `CLAUDE.md` e di `.claude/rules/` non sono verificabili da uno strumento meccanico: una
responsabilità per metodo, nomi espressivi, commenti solo per il razionale, fail fast, niente ponti tra contesti,
l'adapter che non orchestra. I controlli di `reusable-quality.yml` provano import, tipi, stile e test, ma nessuno legge
il codice contro queste regole, e gran parte delle pull request è aperta da agenti in autopilota e integrata con
l'auto-merge. Il proprietario vuole una revisione obbligatoria che blocchi l'integrazione solo per le violazioni di
queste regole, autenticata con il proprio abbonamento Claude invece che con una API key a consumo.

## Opzioni considerate

### 1. `anthropics/claude-code-action` con il token dell'abbonamento del proprietario

- Pro: nessun costo a consumo, nessuna infrastruttura; Claude Code legge `CLAUDE.md` e le rule come in locale.
- Contro: consuma la quota personale condivisa con l'uso interattivo; il token (`claude setup-token`) dura un anno e
  va rinnovato; l'uso automatico di un abbonamento personale non è esplicitamente previsto dai termini d'uso.

### 2. La stessa action con una API key

- Pro: è il percorso documentato per l'automazione; quota e costo separati dall'uso interattivo.
- Contro: costo a consumo per ogni push di ogni pull request.

### 3. Code Review gestita da Anthropic (GitHub App)

- Pro: nessun segreto nel repository.
- Contro: disponibile solo sui piani Team ed Enterprise; il suo controllo non fallisce mai, quindi da solo non blocca.

### 4. Il job fallisce quando trova violazioni

- Pro: blocco esplicito nel controllo.
- Contro: il rilievo resta nel log invece che sulla riga; un falso positivo blocca senza un modo per scavalcarlo che
  non sia rieseguire o modificare il codice.

## Esito della decisione

Scelta: **opzione 1, con il blocco affidato ai thread di review**. Il ruleset `main protetto` richiede già la
risoluzione dei thread (`required_review_thread_resolution`): un thread aperto sulla riga della violazione blocca
l'integrazione, si discute dove sta il codice, e il proprietario può chiudere a mano un falso positivo.

- Flusso `review.yml` (solo trigger) e orchestratore `reusable-review.yml`, job `revisione`: controllo obbligatorio
  `review / revisione`. Parte su `opened`, `synchronize`, `reopened`, `ready_for_review`, non su `edited`: correggere
  la descrizione non consuma quota. È un flusso separato da `quality` per questo motivo.
- L'action `.github/actions/claude-review` incapsula `anthropics/claude-code-action`, fissata per hash, con
  `claude_code_oauth_token` dal segreto di repository `CLAUDE_CODE_OAUTH_TOKEN`, `github_token` del job (nessuna GitHub
  App da installare) e modello `claude-opus-5-5`.
- Il checkout è sul commit base della pull request: Claude Code carica `CLAUDE.md` e le rule di `main`, così una pull
  request non può indebolire le regole con cui viene giudicata. Il codice proposto lo legge dalla storia git
  (`git diff`, `git show` sul commit head), senza scriverlo nella cartella di lavoro.
- Thread inline solo per violazioni di una regola scritta, citandola; nessun rilievo di stile, design o gusto. A ogni
  push la revisione rilegge i propri thread aperti: chiude quelli corretti, non ripete quelli ancora validi.
- Una modifica a `CLAUDE.md`, a `.claude/rules/`, ai contratti di import-linter in `pyproject.toml` o a
  `tests/architecture/known_violations.py` apre un thread che chiede l'approvazione del proprietario: la revisione non
  lo chiude mai, lo chiude il proprietario.
- Se la revisione non si completa (quota esaurita, token scaduto, errore), il job fallisce e la pull request resta
  bloccata fino a una nuova esecuzione.
- Il job è saltato, e per GitHub un job saltato soddisfa il controllo obbligatorio, per `dependabot[bot]` e per le
  pull request da fork, che non ricevono i segreti del repository.
- Permessi del job: `contents: read`, `pull-requests: write`.

### Conseguenze

- `.claude/rules/ci.md` ammette `CLAUDE_CODE_OAUTH_TOKEN` a livello di repository accanto a `SONAR_TOKEN` e stabilisce
  che i thread della revisione li chiude solo la revisione o il proprietario, mai un agente.
- Il controllo `review / revisione` entra nel ruleset `main protetto` dopo l'integrazione: aggiungerlo prima
  bloccherebbe le pull request aperte, che non contengono ancora il flusso.
- Ogni push di ogni pull request consuma quota dell'abbonamento del proprietario: un'esecuzione notturna dell'autopilota
  con molte pull request può esaurirla e bloccare le pull request fino al ripristino.
- Il token va rigenerato ogni anno; scaduto, ogni pull request resta bloccata finché il segreto non viene aggiornato.
- Le pull request di dependabot e da fork si integrano senza revisione AI: le integra il proprietario, a mano.

## Ulteriori informazioni

- Requisito: [#40 - R0.5.1 Controlli di qualità obbligatori sulle pull request]
- Documentazione: <https://code.claude.com/docs/en/github-actions>, <https://code.claude.com/docs/en/authentication>
