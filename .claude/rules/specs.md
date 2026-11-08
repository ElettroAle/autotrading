---
paths:
  - "specs/**"
---

# Specifiche Gherkin

- Percorso: `specs/E<n>-<slug>/F<n>.<m>-<slug>/R<n>.<m>.<k>-<slug>.feature`.
- `# language: it` in prima riga; tag `@R<n>.<m>.<k>`; `Funzionalità: R<n>.<m>.<k> <titolo>`.
- Narrativa `Come` / `Voglio` / `Perché`, poi note e `Fuori ambito:`. Le descrizioni di Epic e Feature
  stanno sulla board, non in file.
- Il requisito dice il COSA: nessun dettaglio tecnico (tabelle, classi, endpoint) negli scenari.
- Linguaggio di business italiano; termini tecnici in inglese quando non serve tradurli (`tenant`).
- Ogni scenario ha almeno un `Allora` verificabile; nessun criterio di accettazione in prosa.
- `@wip` sulla `Funzionalità` finché la User Story non è consegnata; `@pipeline` su scenario o
  `Funzionalità` provati solo da un'esecuzione reale della pipeline, con il link alla run nella PR.
- Ogni file si valida con il parser Gherkin ufficiale prima del commit.
- Dopo una modifica si riallinea la User Story sulla board (titolo, narrativa, criteri di accettazione).
- `docs/requirements.md` è il raw di partenza: non si aggiorna, la fonte di verità sono questi file.
