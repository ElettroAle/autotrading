# ADR 0006 — Immagine base Chainguard e Python 3.15

- Stato: accettata (8 novembre 2026)
- Requisiti: R0.5.1, R0.5.2

## Contesto

Il primo controllo della PR #2 ha trovato 189 vulnerabilità di Trivy nell'immagine
`python:3.12-slim-trixie` (65 LOW, 75 MEDIUM, 49 HIGH, 0 CRITICAL), tutte in pacchetti di sistema
Debian (glibc, util-linux, coreutils…) e quasi tutte senza correzione disponibile, più 6 nel `pip`
dell'immagine base. Le dipendenze Python del progetto non ne avevano. Con la regola "qualunque
severità blocca" (ADR 0004) un'immagine Debian non può passare, a prescindere dalla versione di
Python. Il progetto usava inoltre Python 3.12 invece dell'ultima versione stabile.

## Decisione

- Python **3.15** (ultima stabile, 3.15.2) per progetto, CI e immagine.
- Immagine finale `cgr.dev/chainguard/python:latest`, fase di build `cgr.dev/chainguard/python:latest-dev`:
  basate su Wolfi, ricostruite ogni giorno, senza shell né gestore di pacchetti nell'immagine finale,
  utente non root 65532.
- Entrambe fissate per digest nel `Dockerfile`; Dependabot propone il nuovo digest ogni settimana e
  la CI lo verifica prima del merge.

## Alternative scartate

- **`python:3.15-slim` bloccando solo le CVE correggibili**: cambia la regola "tutte le severità".
- **`python:3.15-slim` con eccezioni in `.trivyignore`**: decine di eccezioni da motivare e
  mantenere a mano.
- **Distroless Debian**: glibc e altre librerie Debian restano, e con loro parte delle CVE.

## Conseguenze

- Il piano gratuito di Chainguard offre solo il tag `latest`: il passaggio a una nuova versione
  maggiore di Python arriva da una PR di Dependabot e va allineato in `pyproject.toml` e nella CI.
- Senza shell nell'immagine finale non si entra nel container con `docker exec … sh`: la diagnosi
  passa da log e `/health`.
