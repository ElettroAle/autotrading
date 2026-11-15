# ADR revisione-che-fallisce-con-thread-aperti — La revisione AI fallisce finché un suo thread resta aperto

- Stato: accettata (15 novembre 2026), decisione del proprietario
- Requisiti: Bug 298 (Task 299), R0.5.1
- Collegate: ADR 0113 (ne sostituisce l'opzione scartata 4: il blocco non è più affidato ai soli thread), ADR 0114

## Contesto e problema

La revisione AI apre un thread per ogni violazione e il ruleset di `main` chiede di risolverli prima
dell'integrazione (ADR 0113), ma il controllo `review / revisione` resta verde. Una pull request con un thread aperto
appare solo «BLOCKED» con tutti i controlli verdi: chi segue i controlli non vede che cosa correggere, e la PR 179 è
rimasta ferma per ore.

## Opzioni considerate

### 1. Thread sulla riga e job che fallisce se restano thread della revisione aperti

- Pro: il rilievo resta sulla riga; il fallimento si vede in `gh pr checks` e in ogni controllo che segue la PR.
- Contro: un thread chiuso a mano non riaccende il controllo finché la revisione non rigira.

### 2. Controllo separato che conta i thread aperti a ogni evento di review

- Pro: riflette subito le chiusure manuali.
- Contro: un workflow in più; i thread aperti dalle persone lo farebbero fallire.

### 3. Nessun cambiamento

- Pro: nessun lavoro.
- Contro: è il difetto.

## Esito della decisione

Scelta: **opzione 1**, decisa dal proprietario. Dopo la revisione, il passo «Thread della revisione aperti» di
`.github/actions/claude-review` legge i `reviewThreads` della pull request con `gh api graphql` e
`tools/review_threads.py` fallisce se resta aperto un thread il cui primo commento è di `github-actions`, elencando
file, riga e regola. Lo script arriva dalla pull request accanto all'action, come l'action stessa (ADR 0113).

### Conseguenze

- Il falso positivo resta gestibile come in ADR 0113: si risponde nel thread motivando, e al push successivo la
  revisione lo chiude se non è una violazione; il controllo torna verde senza chiusure manuali.
- I thread aperti dalle persone non fanno fallire il controllo: li blocca già il ruleset.
