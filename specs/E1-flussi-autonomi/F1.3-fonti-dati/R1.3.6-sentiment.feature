# language: it
@R1.3.6 @wip
Funzionalità: R1.3.6 Fonte sentiment di mercato
  Come utente
  Voglio che l'agente riceva l'indice Fear & Greed del mercato cripto
  Perché tenga conto dell'umore generale del mercato

  A ogni ciclo la fonte rileva l'indice Fear & Greed corrente: valore da 0 a 100, classificazione testuale e
  istante di aggiornamento dell'indice. L'indice riguarda l'intero mercato cripto: compare una sola volta nel
  contesto, non per asset.

  Fuori ambito: sentiment per singolo asset, sentiment dai social.

  Scenario: Indice nel contesto
    Dato che "anna" ha il flusso "alfa" con asset "BTC, ETH" e la fonte "sentiment" attiva
    E che l'indice Fear & Greed vale 72 con classificazione "Greed"
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene una sola volta l'indice Fear & Greed con valore 72 e classificazione "Greed"
    E il contesto riporta l'istante di aggiornamento dell'indice
