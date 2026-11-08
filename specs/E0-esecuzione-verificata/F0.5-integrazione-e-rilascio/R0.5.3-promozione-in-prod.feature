# language: it
@R0.5.3
Funzionalità: R0.5.3 Promozione in prod dello stesso artefatto provato in dev
  Come proprietario
  Voglio portare in prod, con la mia approvazione, esattamente l'artefatto già in esecuzione in dev
  Perché in prod arrivi solo ciò che è stato provato, senza ricostruzioni

  La promozione segue il rilascio in dev nella stessa esecuzione e attende l'approvazione del proprietario.
  La versione di rilascio si calcola dai Conventional Commits dall'ultimo rilascio: "fix:" incrementa la patch, "feat:" la minor, un cambiamento incompatibile ("feat!:" o "fix!:") la major.

  Fuori ambito: ritorno automatico alla versione precedente, rilasci programmati.

  Contesto:
    Dato che l'ultimo rilascio in prod è la versione "1.2.0"
    E che l'installazione dev esegue l'artefatto "1.2.1-dev.57" e ne ha superato il controllo di salute

  @pipeline
  Scenario: Senza approvazione prod non cambia
    Quando il proprietario non approva la promozione
    Allora l'installazione prod resta sulla versione "1.2.0"
    E non viene creato alcun nuovo rilascio

  @pipeline
  Scenario: Con l'approvazione prod esegue lo stesso artefatto di dev
    Quando il proprietario approva la promozione
    Allora il repository ha il rilascio "v1.2.1" sul commit dell'artefatto
    E l'artefatto ha anche la versione "1.2.1" con contenuto identico a "1.2.1-dev.57"
    E l'installazione prod esegue l'artefatto "1.2.1"
    E l'installazione prod risponde al controllo di salute dichiarando la versione "1.2.1" e l'ambiente "prod"

  Schema dello scenario: La versione di rilascio segue i Conventional Commits
    Dato che dopo il rilascio "1.2.0" il ramo principale contiene i commit "<commit>"
    Quando il proprietario approva la promozione
    Allora il nuovo rilascio è "<versione>"

    Esempi:
      | commit                      | versione |
      | fix: a, fix: b              | v1.2.1   |
      | fix: a, feat: b             | v1.3.0   |
      | feat!: a, fix: b            | v2.0.0   |
      | docs: a, chore: b           | v1.2.1   |

  Scenario: Un commit non conforme blocca la promozione
    Dato che dopo il rilascio "1.2.0" il ramo principale contiene un commit "aggiornato tutto"
    Quando il proprietario approva la promozione
    Allora la promozione fallisce indicando il commit non conforme ai Conventional Commits
    E l'installazione prod resta sulla versione "1.2.0"

  @pipeline
  Scenario: Un rilascio in prod non riuscito è dichiarato
    Dato che dopo il rilascio in prod il controllo di salute non risponde entro 2 minuti
    Quando il proprietario approva la promozione
    Allora l'esecuzione fallisce indicando "controllo di salute non superato in prod"
