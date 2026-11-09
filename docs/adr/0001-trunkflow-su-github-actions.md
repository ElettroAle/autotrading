# ADR 0001 — Flusso TrunkFlow su GitHub Actions a tre livelli

- Stato: accettata (8 novembre 2026)
- Requisiti: R0.5.1, R0.5.2, R0.5.3, R0.5.4

## Contesto

Il proprietario usa TrunkFlow nella libreria ADO `ElettroAle/Pipelines` V3: un solo ramo, CI che
produce pre-release, promozione manuale che crea il tag SemVer. Questo repository vive su GitHub,
il deploy passa sempre dalla pipeline con runner ospitati da GitHub (`docs/architecture.md` §12.1).

## Decisione

Stessa struttura a livelli di V3, tradotta in GitHub Actions:

| Livello V3 | Qui |
|---|---|
| Entry point | `.github/workflows/{quality,release,provision,inspect}.yml`: solo trigger e parametri |
| Orchestratore (`Modules/`) | `.github/workflows/reusable-*.yml`: job e ordine, nessun comando |
| Step template (`Common/Steps/`) | `.github/actions/<tecnologia>-<azione>/action.yml`: l'unico posto con i comandi |

- `quality.yml` sulle pull request verso `main`: un job per controllo, ognuno obbligatorio nel
  ruleset.
- `release.yml` sul push in `main`: versione, artefatto, rilascio dev, promozione prod.
- `provision.yml` ad avvio manuale per ambiente.
- `inspect.yml` ad avvio manuale per ambiente: legge quote, rete e risorse del progetto OVH senza
  modificare nulla.
- Action di terzi fissate per hash di commit; strumenti scaricati dalle release con verifica del
  checksum.

## Alternative scartate

- **Libreria esterna riusabile** come il repository Pipelines: con un solo repository consumatore è
  prematura; la struttura a livelli permette di estrarla in seguito senza riscrivere.
- **Workflow piatti con i comandi in linea**: duplicazione tra quality e release (build, scansione).

## Conseguenze

- Ogni operazione tecnologica si modifica in un solo file.
- I nomi dei job di `reusable-quality.yml` sono i controlli obbligatori del ruleset: rinominarne
  uno richiede di aggiornare il ruleset.
