# ADR campi-delle-credenziali-fuori-dall-autocompletamento — Campi delle credenziali fuori dall'autocompletamento e motivo dell'exchange nella dashboard

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 387 (Task 389), R2.3.1, R2.3.9
- Collegate: ADR credenziali-senza-caratteri-invisibili-e-forma-diagnosticabile, ADR 0130, ADR 0131

## Contesto e problema

Nel modulo dei conti il campo segreto ha `autocomplete="off"`. Chrome e i password manager (LastPass, 1Password,
Bitwarden) ignorano quel valore sui campi password e possono riempire il campo, o quello accanto, con una password
salvata per il sito: il valore inviato non è quello incollato. Inoltre, quando l'exchange rifiuta le credenziali, la
dashboard mostra solo «credenziali rifiutate dall'exchange» e il motivo dell'exchange (`exchange_message` nei Problem
Details) resta nella risposta, visibile solo dagli strumenti del browser.

## Opzioni considerate

### 1. Attributi che escludono i campi dichiarati dall'autocompletamento e motivo dell'exchange accodato al titolo

- Pro: `autocomplete="new-password"` è rispettato da Chrome; `data-lpignore`, `data-1p-ignore` e `data-bwignore`
  escludono i password manager più diffusi; vale per ogni campo che un adapter dichiara, senza nominare exchange.
- Pro: il lettore dei Problem Details accoda `exchange_message` al motivo quando c'è: ogni modulo lo mostra, accanto
  al campo nominato o in testa al modulo.
- Contro: attributi proprietari dei password manager nel componente comune.

### 2. Campo segreto come testo con maschera CSS

- Pro: nessun password manager lo considera una password.
- Contro: maschera non standard, il valore è leggibile da estensioni e accessibilità come testo.

## Esito della decisione

Opzione 1. I campi che un adapter dichiara (`DeclaredFields`) portano `autocomplete="new-password"` se segreti,
`autocomplete="off"` altrimenti, e gli attributi `data-lpignore`, `data-1p-ignore`, `data-bwignore`.
`problemDetailsOf` legge `exchange_message` e lo accoda al motivo («credenziali rifiutate dall'exchange: …») in
registrazione e sostituzione delle credenziali, e in ogni altra risposta che lo porta.
