# language: it
@R0.2.5
Funzionalità: R0.2.5 Rimozione di un conto
  Come utente
  Voglio rimuovere un conto che non uso più
  Perché la piattaforma non conservi credenziali non necessarie

  La rimozione elimina le credenziali; lo storico delle operazioni del conto resta consultabile.
  La rimozione non tocca le posizioni sull'exchange.

  Fuori ambito: il vincolo sui flussi attivi assegnati al conto, introdotto insieme ai flussi.

  Contesto:
    Dato che "anna" ha il conto "test-1" con le credenziali "K1"

  Scenario: Rimozione di un conto senza posizioni aperte
    Dato che il conto "test-1" non ha posizioni aperte sull'exchange
    Quando "anna" rimuove il conto "test-1"
    Allora il conto "test-1" non compare più tra i conti di "anna"
    E le credenziali "K1" non sono più conservate dalla piattaforma
    E lo storico delle operazioni del conto "test-1" resta consultabile

  Scenario: Rimozione di un conto con posizioni aperte chiede conferma
    Dato che il conto "test-1" ha una posizione aperta su "BTC" sull'exchange
    Quando "anna" rimuove il conto "test-1" senza confermare
    Allora la rimozione è sospesa con il motivo "il conto ha posizioni aperte che resteranno sull'exchange senza gestione"
    E il conto "test-1" resta tra i conti di "anna"

  Scenario: Rimozione confermata di un conto con posizioni aperte
    Dato che il conto "test-1" ha una posizione aperta su "BTC" sull'exchange
    Quando "anna" rimuove il conto "test-1" confermando
    Allora il conto "test-1" non compare più tra i conti di "anna"
    E la posizione su "BTC" resta aperta sull'exchange
