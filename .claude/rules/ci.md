---
paths:
  - ".github/**"
  - "deploy/**"
  - "tools/**"
  - "Dockerfile"
  - "cliff.toml"
  - "sonar-project.properties"
---

# Pipeline, rilascio e installazioni

Decisioni in `docs/adr/0001`-`0011`. Requisiti in `specs/E0-esecuzione-verificata/F0.5-*`.

## Struttura a livelli (come Pipelines V3)

- `.github/workflows/<flusso>.yml`: solo trigger, parametri e chiamata all'orchestratore.
- `.github/workflows/reusable-<flusso>.yml`: job, ordine, environment, permessi. Nessun comando
  `run:`: solo `uses:` di action.
- `.github/actions/<tecnologia>-<azione>/action.yml`: l'unico posto con i comandi. Un'operazione si
  definisce una volta sola e si riusa.

## Regole

- Action di terzi solo fissate per hash di commit, con la versione in commento.
- Strumenti scaricati dalle release solo con verifica del checksum.
- Valori dagli input o dai contesti GitHub passano ai comandi sempre via `env:`, mai interpolati
  in `run:`.
- Segreti solo negli environment `dev` e `prod` (o `SONAR_TOKEN` a livello di repository); mai
  variabili d'ambiente sulla macchina, mai credenziali che restano dopo l'esecuzione.
- Permessi minimi per job (`contents: read` salvo necessità dichiarata).
- I nomi dei job di `reusable-quality.yml` sono i controlli obbligatori del ruleset di `main`.
- Il deploy usa sempre il digest dell'immagine; la promozione non ricostruisce.
- `tools/` contiene gli script Python della pipeline: fuori dall'esagono, stessi principi di codice,
  unit test in `tests/unit/tools/`. Ogni errore discende da `tools.errors.PipelineError`.
- Workflow validati con actionlint prima del commit.
