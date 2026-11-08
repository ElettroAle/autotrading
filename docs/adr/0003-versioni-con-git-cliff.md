# ADR 0003 — Versioni e controllo dei Conventional Commits con git-cliff

- Stato: accettata (8 novembre 2026)
- Requisiti: R0.5.1, R0.5.2, R0.5.3

## Contesto

V3 usa git-cliff con un unico `cliff.toml` per bump, controllo del titolo e note di rilascio.

## Decisione

- `cliff.toml` ripreso da V3, senza il preprocessore dei messaggi "Merged PR" di Azure DevOps.
- Il merge in `main` avviene solo per squash: il titolo della PR diventa il messaggio del commit,
  quindi si controlla il titolo come un commit vero (commit staccato valutato da git-cliff).
- Pre-release: `<prossima versione>-dev.<numero esecuzione>`; se dall'ultimo rilascio non ci sono
  commit che incrementano, si incrementa la patch, come in V3.
- Alla promozione: tutti i commit dall'ultimo tag devono essere conformi, poi tag `vX.Y.Z`.
- La logica è in `tools/release_version.py`, provata da unit test e dagli scenari di R0.5.3 su
  repository Git temporanei.

## Alternative scartate

- **Script PowerShell di V3**: richiederebbero pwsh e Pester accanto all'ecosistema Python.
- **Regex propria per i titoli**: seconda fonte delle regole, divergerebbe da `cliff.toml`.

## Conseguenze

- `git-cliff` è una dipendenza di sviluppo installata da PyPI, stessa versione in locale e in CI.
