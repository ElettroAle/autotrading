# language: it
@R0.1.2
Funzionalità: R0.1.2 Spazio dell'utente creato al primo accesso
  Come utente con il ruolo Utente
  Voglio trovare il mio spazio pronto al primo accesso
  Perché conti, flussi e dati abbiano da subito un proprietario

  Fuori ambito: eliminazione dello spazio, trasferimento di uno spazio ad altro utente, condivisione di spazi.

  Scenario: Al primo accesso nasce uno spazio vuoto
    Dato che la persona "anna" ha il ruolo "Utente" e non è mai entrata
    Quando "anna" accede alla piattaforma
    Allora la piattaforma crea uno spazio intestato ad "anna"
    E lo spazio di "anna" non contiene conti
    E lo spazio di "anna" non contiene flussi

  Scenario: Agli accessi successivi lo spazio è lo stesso
    Dato che "anna" ha uno spazio con il conto "test-1"
    Quando "anna" accede di nuovo alla piattaforma
    Allora la piattaforma non crea un secondo spazio per "anna"
    E lo spazio di "anna" contiene il conto "test-1"

  Scenario: Lo spazio è legato all'identificativo della directory, non al nome
    Dato che "anna" ha uno spazio
    E che nella directory il nome visualizzato di "anna" cambia in "Anna Rossi"
    Quando "anna" accede di nuovo alla piattaforma
    Allora "anna" ritrova lo stesso spazio
