# ADR casi-della-descrizione-negli-scenari — I casi della descrizione e dei Bug diventano scenari, senza toccare la produzione

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 672 (Task 673-678)
- Collegate: ADR nessun-test-escluso-o-saltato; `.claude/rules/specs.md`, `.claude/rules/tests.md`
- Verifica: prova

## Contesto e problema

Il controllo del Task 645 ha trovato 130 casi dichiarati nella descrizione di una User Story o corretti da un suo Bug
che nessuno scenario dei criteri di accettazione prova. Il comportamento c'è, spesso coperto da unit test, ma una
modifica futura può romperlo senza che uno scenario diventi rosso.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): contano gli scenari nei criteri di accettazione; i casi
  mancanti vanno prima sulla board e poi nel `.feature`.
- Decisione del proprietario: il comportamento dell'app oggi è corretto, non si attendono cambi al codice.
- `tests.md`: gli scenari si eseguono sui casi d'uso con gli adapter finti; ogni `Allora` e ogni `E` ha la sua
  asserzione; ogni prova si vede rossa prima di diventare verde.

## Decisione

- Ogni caso del gruppo diventa uno scenario (o una riga di Esempi di uno schema esistente) nel `.feature` della sua
  User Story, nel dialetto e con i passi già usati dal file; i passi nuovi si legano nei moduli di scenario esistenti.
- Lo scenario descrive ciò che il codice fa oggi. Il rosso si vede togliendo per un momento la riga di produzione
  che realizza il caso, poi ripristinata.
- Nessuna modifica al codice di produzione. Se il codice non fa ciò che la descrizione dice, il caso non si scrive:
  si riporta con file e riga, e decide il proprietario.
- Un caso che appartiene a un'altra User Story va nel `.feature` di quella.
- Prima della pull request i criteri di accettazione sulla board si riallineano ai `.feature` cambiati.

## Alternative scartate

- Lasciare i casi solo negli unit test: non stanno nei criteri di accettazione, che sono la prova del requisito.

## Conseguenze

- Gli scenari crescono di circa 130; la copertura degli scenari resta al 100%.
