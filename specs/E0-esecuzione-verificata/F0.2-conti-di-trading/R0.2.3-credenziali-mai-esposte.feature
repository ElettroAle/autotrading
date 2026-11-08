# language: it
@R0.2.3 @wip
Funzionalità: R0.2.3 Credenziali dei conti mai esposte
  Come utente
  Voglio che le credenziali che inserisco non siano mai più leggibili dopo il salvataggio
  Perché chi accede ai miei dati, ai registri o alle risposte non possa operare al posto mio

  Le credenziali sono custodite in un archivio di segreti separato dai dati della piattaforma.
  Solo il servizio della piattaforma le usa per parlare con l'exchange; le persone con il ruolo Gestore chiavi possono amministrarle nell'archivio.

  Fuori ambito: rotazione automatica delle credenziali, scadenza delle chiavi sull'exchange.

  Contesto:
    Dato che "anna" ha registrato il conto "test-1" con le credenziali "K1"

  Scenario: Il dettaglio del conto non contiene le credenziali
    Quando "anna" chiede il dettaglio del conto "test-1"
    Allora il dettaglio non contiene "K1"
    E il dettaglio indica che le credenziali sono presenti

  Scenario: I registri della piattaforma non contengono le credenziali
    Quando la piattaforma registra un'operazione sul conto "test-1"
    Allora nessun registro della piattaforma contiene "K1"

  Scenario: I dati della piattaforma non contengono le credenziali in chiaro
    Quando si esaminano i dati salvati della piattaforma per il conto "test-1"
    Allora i dati salvati non contengono "K1"

  Scenario: Un errore dell'exchange non riporta le credenziali
    Dato che l'exchange restituisce un errore per un'operazione sul conto "test-1"
    Quando la piattaforma riporta l'errore ad "anna"
    Allora l'errore riportato non contiene "K1"
