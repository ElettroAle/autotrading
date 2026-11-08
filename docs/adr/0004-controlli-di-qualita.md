# ADR 0004 — Controlli di qualità bloccanti

- Stato: accettata (8 novembre 2026)
- Requisiti: R0.5.1

## Decisione

| Controllo | Strumento |
|---|---|
| segreti | gitleaks v8.30.1 su tutta la storia |
| titolo | git-cliff (ADR 0003) |
| stile | ruff check e ruff format |
| tipi | mypy strict |
| architettura | import-linter, contratti in `pyproject.toml` |
| test | pytest: unit, scenari pytest-bdd, test architetturale |
| copertura del codice | `tools/coverage_gate.py`: 90% domain e application, 80% totale |
| specifiche | parser Gherkin ufficiale su `specs/` |
| copertura degli scenari | `tools/scenario_coverage.py` sul report Cucumber JSON di pytest-bdd |
| vulnerabilità | pip-audit sulle dipendenze, Trivy sull'immagine; qualunque severità blocca |
| analisi statica | SonarCloud con quality gate atteso |

- Scenari esclusi dalla copertura automatica: `@wip` (User Story non ancora consegnata, il tag si
  toglie consegnandola) e `@pipeline` (provati da un'esecuzione reale della pipeline, con evidenza
  nella PR).
- Ruleset su `main`: solo pull request, solo squash, tutti i controlli obbligatori, niente force
  push né cancellazione. Possibile solo con il repository pubblico (GitHub Free), reso pubblico
  dopo gitleaks pulito sulla storia.
- Dependabot apre PR settimanali per dipendenze Python, action e immagine base.

## Alternative scartate

- **Bloccare solo HIGH e CRITICAL**: scartata dal proprietario.
- **Copertura degli scenari in sola segnalazione**: contraddice "tutti bloccanti".

## Conseguenze

- Una vulnerabilità senza correzione disponibile, di qualunque severità, blocca le PR finché
  l'immagine base o la dipendenza non la risolvono: è il prezzo accettato del blocco totale.
  L'immagine base Chainguard (ADR 0006) riduce i pacchetti di sistema al minimo e li ricostruisce ogni giorno.
- I test di integrazione contro servizi entrano nei controlli con il primo adapter.
