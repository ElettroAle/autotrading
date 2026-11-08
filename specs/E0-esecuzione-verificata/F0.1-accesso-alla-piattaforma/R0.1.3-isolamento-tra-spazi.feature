# language: it
@R0.1.3
Funzionalità: R0.1.3 Isolamento dei dati tra spazi
  Come utente
  Voglio che nessun altro utente veda o modifichi ciò che appartiene al mio spazio
  Perché conti, credenziali e risultati sono personali

  Fuori ambito: condivisione volontaria tra utenti, funzioni di amministrazione trasversali agli spazi.

  Contesto:
    Dato che "anna" e "bruno" hanno il ruolo "Utente"
    E che "anna" ha nel proprio spazio il conto "conto-anna"

  Scenario: Un utente non vede i conti di un altro spazio
    Quando "bruno" chiede l'elenco dei propri conti
    Allora l'elenco dei conti di "bruno" non contiene "conto-anna"

  Scenario: Un elemento di un altro spazio risulta inesistente
    Quando "bruno" chiede il dettaglio del conto "conto-anna" indicandone l'identificativo
    Allora la richiesta di "bruno" è respinta con l'esito "non trovato"
    E l'esito non rivela che "conto-anna" esiste in un altro spazio

  Scenario: Un utente non modifica gli elementi di un altro spazio
    Quando "bruno" chiede di sostituire le credenziali del conto "conto-anna"
    Allora la richiesta di "bruno" è respinta con l'esito "non trovato"
    E le credenziali di "conto-anna" restano invariate
