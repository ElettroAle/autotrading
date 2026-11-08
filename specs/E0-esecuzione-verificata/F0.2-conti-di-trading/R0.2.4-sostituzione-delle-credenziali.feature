# language: it
@R0.2.4
Funzionalità: R0.2.4 Sostituzione delle credenziali di un conto
  Come utente
  Voglio sostituire le credenziali di un mio conto
  Perché possa ruotare una chiave o rimediare a una chiave scaduta senza ricreare il conto

  Fuori ambito: cambio dell'exchange di un conto (si registra un conto nuovo).

  Contesto:
    Dato che "anna" ha il conto "test-1" con le credenziali "K1"

  Scenario: Sostituzione con credenziali accettate
    Quando "anna" sostituisce le credenziali del conto "test-1" con "K2" che l'exchange accetta
    Allora il conto "test-1" usa le credenziali "K2"
    E le credenziali "K1" sono eliminate dall'archivio dei segreti

  Scenario: Sostituzione con credenziali rifiutate
    Quando "anna" sostituisce le credenziali del conto "test-1" con "K3" che l'exchange rifiuta
    Allora la sostituzione fallisce con il motivo "credenziali rifiutate dall'exchange"
    E il conto "test-1" continua a usare le credenziali "K1"

  Scenario: Le nuove credenziali appartengono a un altro conto dell'exchange
    Quando "anna" sostituisce le credenziali del conto "test-1" con credenziali valide di un diverso conto dell'exchange
    Allora la sostituzione fallisce con il motivo "le credenziali appartengono a un altro conto dell'exchange"
    E il conto "test-1" continua a usare le credenziali "K1"
