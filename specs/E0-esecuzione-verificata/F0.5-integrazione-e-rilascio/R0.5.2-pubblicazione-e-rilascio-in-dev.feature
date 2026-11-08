# language: it
@R0.5.2 @pipeline
Funzionalità: R0.5.2 Pubblicazione dell'artefatto e rilascio automatico in dev
  Come proprietario
  Voglio che ogni modifica integrata nel ramo principale venga pubblicata una sola volta e rilasciata subito in dev
  Perché ogni modifica sia provata nell'installazione dev con l'artefatto che potrà andare in prod

  L'artefatto è l'immagine del servizio, costruita una sola volta per ogni integrazione.
  La versione dell'artefatto in dev è una pre-release della prossima versione: "<prossima versione>-dev.<numero dell'esecuzione>".
  La prossima versione si calcola dai Conventional Commits successivi all'ultimo rilascio; senza rilasci precedenti parte da 0.1.0.

  Fuori ambito: rilascio in prod (R0.5.3), creazione delle installazioni (R0.5.4).

  Contesto:
    Dato che l'ultimo rilascio in prod è la versione "1.2.0"
    E che il ramo principale contiene dopo il rilascio solo commit "fix:"

  Scenario: Ogni integrazione pubblica un artefatto con versione di pre-release
    Quando una pull request viene integrata nel ramo principale nell'esecuzione numero 57
    Allora il registro delle immagini contiene l'artefatto con versione "1.2.1-dev.57"
    E l'artefatto è associato al commit integrato

  Scenario: L'installazione dev riceve l'artefatto appena pubblicato
    Quando l'artefatto "1.2.1-dev.57" è pubblicato
    Allora l'installazione dev esegue l'artefatto "1.2.1-dev.57"
    E l'installazione dev risponde al controllo di salute dichiarando la versione "1.2.1-dev.57" e l'ambiente "dev"

  Scenario: Un artefatto con vulnerabilità non viene pubblicato
    Dato che l'immagine costruita contiene un pacchetto con una vulnerabilità nota di qualunque severità
    Quando l'integrazione viene elaborata
    Allora l'artefatto non è pubblicato nel registro
    E l'installazione dev resta sulla versione precedente

  Scenario: Un rilascio in dev non riuscito ferma la catena
    Dato che dopo il rilascio in dev il controllo di salute non risponde entro 2 minuti
    Quando l'integrazione viene elaborata
    Allora l'esecuzione fallisce indicando "controllo di salute non superato in dev"
    E la promozione in prod non è proponibile per quell'artefatto
