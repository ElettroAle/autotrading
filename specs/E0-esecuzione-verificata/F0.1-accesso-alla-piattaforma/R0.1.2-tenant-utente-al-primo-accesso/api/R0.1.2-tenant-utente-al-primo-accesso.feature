# language: it
@R0.1.2
Funzionalità: R0.1.2 Tenant dell'utente creato al primo accesso
  Come utente con il ruolo Utente
  Voglio trovare il mio tenant pronto al primo accesso
  Perché conti, flussi e dati abbiano da subito un proprietario

  Fuori ambito: eliminazione del tenant, trasferimento di un tenant ad altro utente, condivisione di tenant.

  Scenario: Al primo accesso nasce un tenant vuoto
    Dato che la persona "anna" ha il ruolo "Utente" e non è mai entrata
    Quando "anna" accede alla piattaforma
    Allora la piattaforma crea un tenant intestato ad "anna"
    E il tenant di "anna" non contiene conti
    E il tenant di "anna" non contiene flussi

  Scenario: Agli accessi successivi il tenant è lo stesso
    Dato che "anna" ha un tenant con il conto "test-1"
    Quando "anna" accede di nuovo alla piattaforma
    Allora la piattaforma non crea un secondo tenant per "anna"
    E il tenant di "anna" contiene il conto "test-1"

  Scenario: Il tenant è legato all'identificativo della directory, non al nome
    Dato che "anna" ha un tenant
    E che nella directory il nome visualizzato di "anna" cambia in "Anna Rossi"
    Quando "anna" accede di nuovo alla piattaforma
    Allora "anna" ritrova lo stesso tenant
