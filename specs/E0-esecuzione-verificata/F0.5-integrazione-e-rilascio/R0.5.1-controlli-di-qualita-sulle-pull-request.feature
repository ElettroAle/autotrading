# language: it
@R0.5.1
Funzionalità: R0.5.1 Controlli di qualità obbligatori sulle pull request
  Come proprietario del repository
  Voglio che nessuna modifica entri nel ramo principale senza pull request e senza controlli superati
  Perché il ramo principale sia sempre rilasciabile

  Il ramo principale accetta solo pull request integrate in un unico commit, il cui messaggio è il titolo della pull request.
  I controlli sono tutti bloccanti.
  Soglie di copertura del codice dagli unit test: 90% sul livello domain e sul livello application, 80% sul totale.

  Ogni pull request riceve una revisione AI che verifica le regole del repository: CLAUDE.md e le rule che coprono i file modificati.
  Le regole valutate sono quelle del ramo principale, mai quelle che la pull request propone.
  Ogni violazione apre un thread sulla riga che la contiene; un thread aperto blocca l'integrazione.

  Fuori ambito: revisione obbligatoria da parte di un'altra persona, test di integrazione contro servizi (entrano con il primo adapter), rilievi di stile, design o gusto che non violano una regola scritta.

  @pipeline
  Scenario: Un push diretto sul ramo principale è rifiutato
    Quando qualcuno invia un commit direttamente sul ramo principale
    Allora il ramo principale rifiuta il commit
    E il ramo principale resta invariato

  @pipeline
  Scenario: Una pull request con tutti i controlli superati si può integrare
    Dato che una pull request supera tutti i controlli
    Quando il proprietario chiede di integrarla
    Allora la pull request è integrata nel ramo principale come un unico commit

  @pipeline
  Schema dello scenario: Un controllo fallito blocca l'integrazione
    Dato che una pull request contiene "<difetto>"
    Quando i controlli di qualità vengono eseguiti
    Allora il controllo "<controllo>" fallisce
    E la pull request non si può integrare

    Esempi:
      | difetto                                                             | controllo                 |
      | un segreto scritto nel codice o nella storia dei commit              | segreti                   |
      | un titolo che non segue i Conventional Commits                      | titolo                    |
      | codice non conforme alle regole di stile o di formattazione         | stile                     |
      | un errore di tipo                                                   | tipi                      |
      | un import che viola la regola delle dipendenze tra livelli          | architettura              |
      | un test che fallisce                                                | test                      |
      | un file di scenari che non rispetta la sintassi Gherkin             | specifiche                |
      | uno scenario delle specifiche non eseguito o non superato           | copertura degli scenari   |
      | una dipendenza con una vulnerabilità nota di qualunque severità     | vulnerabilità             |
      | un problema bloccante segnalato dall'analisi statica del codice     | analisi statica           |

  Schema dello scenario: La copertura del codice sotto soglia blocca l'integrazione
    Dato che con la pull request la copertura degli unit test su "<ambito>" è <copertura>%
    Quando i controlli di qualità vengono eseguiti
    Allora il controllo "copertura del codice" fallisce indicando la soglia <soglia>% per "<ambito>"

    Esempi:
      | ambito      | copertura | soglia |
      | domain      | 89        | 90     |
      | application | 85        | 90     |
      | totale      | 79        | 80     |

  Scenario: La copertura del codice alle soglie è accettata
    Dato che con la pull request la copertura è 90% su domain, 90% su application e 80% sul totale
    Quando i controlli di qualità vengono eseguiti
    Allora il controllo "copertura del codice" è superato

  @pipeline
  Scenario: Una violazione delle regole del repository apre un thread che blocca l'integrazione
    Dato che una pull request contiene una modifica che viola una regola di CLAUDE.md o di una rule che copre il file modificato
    Quando la revisione AI esamina la pull request
    Allora la revisione apre un thread sulla riga della modifica citando la regola violata
    E la pull request non si può integrare finché il thread resta aperto

  @pipeline
  Scenario: La correzione della violazione chiude il thread
    Dato che una pull request ha un thread aperto dalla revisione AI
    Quando l'autore invia un commit che corregge la violazione
    Allora la revisione chiude il thread
    E la pull request si può integrare

  @pipeline
  Scenario: Una modifica alle regole del repository attende il proprietario
    Dato che una pull request modifica CLAUDE.md, una rule, un contratto di architettura o l'elenco delle violazioni note
    Quando la revisione AI esamina la pull request
    Allora la revisione apre un thread che chiede l'approvazione del proprietario
    E il thread lo chiude solo il proprietario

  @pipeline
  Scenario: Una revisione che non si completa blocca l'integrazione
    Dato che la revisione AI non riesce a completare l'esame della pull request
    Quando i controlli della pull request terminano
    Allora il controllo "revisione" fallisce
    E la pull request non si può integrare
