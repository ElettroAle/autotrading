# ADR 0114 — Revisione AI senza controllo dei cambi alle regole

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.5.1 (Task T0.5.6)
- Sostituisce in parte: ADR 0113 (il punto sulle modifiche alle regole e alla revisione)

## Contesto e problema

L'ADR 0113 chiedeva un'ADR nella stessa pull request per ogni modifica a `CLAUDE.md`, alle rule, ai contratti di
architettura, a `tests/architecture/known_violations.py` e alla revisione stessa. La prima pull request dopo
l'integrazione (#131) è rimasta bloccata perché toglieva due voci dall'elenco delle violazioni note, cioè correggeva un
Bug: un falso positivo. Il proprietario vuole una revisione semplice, che controlli il codice con le regole e basta.

## Opzioni considerate

### 1. Restringere il controllo ai cambi che allentano una regola

- Contro: un giudizio in più per il modello, e altri casi limite da scrivere.

### 2. Togliere il controllo dei cambi alle regole

- Pro: la revisione fa una cosa sola, giudicare il codice con le regole.
- Contro: un cambio alle regole non è segnalato dalla revisione.

## Esito della decisione

Scelta: **opzione 2**. La revisione giudica il codice della pull request con `CLAUDE.md` e le rule che la pull
request porta; una modifica alle regole o alla revisione non è mai di per sé una violazione. Il resto dell'ADR 0113
resta valido.

### Conseguenze

- `.claude/rules/ci.md` e R0.5.1 perdono la condizione dell'ADR per i cambi alle regole, e R0.5.1 i due scenari che la
  provavano.
- Un cambio alle regole si vede solo nel diff della pull request.
