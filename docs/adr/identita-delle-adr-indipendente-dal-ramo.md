# ADR identita-delle-adr-indipendente-dal-ramo — Una nuova ADR si chiama col suo titolo, non con un numero scelto nel ramo

- Stato: accettata (15 novembre 2026), decisione del proprietario (numero non più scelto nel ramo)
- Requisiti: Bug 294 (Task 295)
- Collegate: ADR 0084 (work item nelle PR), ADR 0113 (revisione AI)

## Contesto e problema

Il numero `NNNN` di una ADR si sceglie quando si apre il ramo. Con più sessioni in parallelo due pull request prendono
lo stesso numero: la seconda, aggiornata su `main`, fallisce `tests/architecture/test_adr_numbers.py` e va rinumerata a
mano con riferimenti, Task e corpo della PR, poi si riattendono tutti i controlli (PR 168 con 0155 e 0156, PR 172 con
0162). Il proprietario chiede che l'identità di una decisione non dipenda più dal ramo.

Vincoli: `main` accetta solo pull request integrate per squash con i controlli obbligatori, senza attori che scavalcano
il ruleset; il repository è di un utente, quindi niente merge queue.

## Opzioni considerate

### 1. Job dopo l'integrazione che rinomina l'ADR col numero successivo e fa commit su `main`

- Pro: numeri consecutivi nell'ordine d'integrazione.
- Contro: il ruleset di `main` non ammette commit diretti; servirebbe un attore che lo scavalca, cioè allentare la
  protezione.

### 2. Pull request automatica di rinumerazione dopo l'integrazione

- Pro: passa dal ruleset.
- Contro: una pull request aperta col `GITHUB_TOKEN` non avvia i workflow, quindi i controlli obbligatori non partono e
  resta bloccata; servirebbe un token personale o una GitHub App.

### 3. Workflow che rinumera nel ramo della pull request prima dell'integrazione

- Pro: il numero arriva vicino all'integrazione.
- Contro: un push del `GITHUB_TOKEN` non avvia i controlli sul nuovo commit; senza ramo aggiornato obbligatorio la
  collisione resta possibile.

### 4. Nuove ADR senza numero, `docs/adr/<titolo>.md`, ordine dalla storia di `main`

- Pro: nessuna collisione d'identità (due file con lo stesso nome sono un conflitto visibile); nessun allentamento del
  ruleset né token; nessun passo manuale.
- Contro: niente numero progressivo per le nuove decisioni; i riferimenti, scritti col titolo, sono più lunghi.

## Esito della decisione

Scelta: **opzione 4**. È l'unica che elimina la collisione rispettando il ruleset senza attori di bypass né token
personali: le opzioni 1-3 chiedono di allentare la protezione di `main` o un'identità con più permessi. L'ordine
d'integrazione lo conserva la storia di `main` (il commit di squash che aggiunge il file).

- Una nuova ADR è `docs/adr/<titolo-in-kebab-case>.md` e comincia con `# ADR <titolo-in-kebab-case> — Titolo`; un
  riferimento si scrive `ADR <titolo-in-kebab-case>`. Il Task sulla board cita l'ADR col suo percorso.
- Le ADR numerate restano col loro numero e i loro riferimenti. I numeri sono congelati all'ultimo dato in un ramo
  (0168, comprese le decisioni ancora aperte in PR quando la numerazione si è fermata): un nuovo file numerato è un
  test rosso che dice il nome da usare.
- `tests/architecture/test_adr_numbers.py` verifica numeri unici e titolo col numero per le numerate, nessun numero
  oltre l'ultimo, nome in kebab-case e titolo col nome del file per le nuove. `CLAUDE.md` dice la forma.

Scostamento dalla richiesta: il numero non lo assegna la pipeline all'integrazione, perché sotto il ruleset attuale
nessun job può scrivere su `main` né far partire i controlli su un proprio commit. Il risultato chiesto, nessuna
collisione tra rami paralleli e ordine dato dall'integrazione, resta.

### Conseguenze

- Una pull request in volo con una nuova ADR numerata oltre 0168 la rinomina al titolo una volta; poi le collisioni
  spariscono.
