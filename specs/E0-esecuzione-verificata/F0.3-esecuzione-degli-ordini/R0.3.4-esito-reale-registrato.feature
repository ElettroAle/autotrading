# language: it
@R0.3.4
Funzionalità: R0.3.4 Registrazione dell'esito reale degli ordini
  Come utente
  Voglio che ogni ordine sia registrato con ciò che l'exchange ha effettivamente eseguito
  Perché risultati e commissioni corrispondano alla realtà e non a quanto atteso

  Fuori ambito: attribuzione degli ordini ai flussi (arriva con i flussi).

  Contesto:
    Dato che il conto "test-1" è su "Hyperliquid"

  Scenario: Ordine eseguito interamente
    Quando la piattaforma invia sul conto "test-1" un ordine di apertura che l'exchange esegue
    Allora l'ordine è registrato con la dimensione eseguita letta dall'exchange
    E l'ordine è registrato con il prezzo medio di esecuzione letto dall'exchange
    E l'ordine è registrato con la commissione letta dall'exchange
    E l'ordine è registrato con l'istante di esecuzione letto dall'exchange

  Scenario: Ordine eseguito solo in parte
    Dato che l'exchange esegue solo il 60% della dimensione richiesta
    Quando la piattaforma invia sul conto "test-1" un ordine di apertura
    Allora l'ordine è registrato come "eseguito in parte"
    E l'ordine è registrato con la dimensione richiesta e la dimensione eseguita

  Scenario: La registrazione riporta l'origine dell'ordine
    Quando la procedura di verifica invia un ordine sul conto "test-1"
    Allora l'ordine è registrato con l'origine "procedura di verifica"
