# language: it
@R0.2.4
Funzionalità: R0.2.4 Sostituzione delle credenziali di un conto
  Come utente
  Voglio sostituire le credenziali di un mio conto
  Perché possa ruotare una chiave o rimediare a una chiave scaduta senza ricreare il conto

  Fuori ambito: cambio dell'exchange di un conto (si registra un conto nuovo).

  La sostituzione chiede solo i campi segreti che l'exchange dichiara: i campi pubblici, come l'indirizzo del conto,
  restano quelli registrati e il conto li mostra (Bug 401).

  Contesto:
    Dato che "anna" ha il conto "test-1" con le credenziali "K1"

  Scenario: Sostituzione con credenziali accettate
    Quando "anna" sostituisce i campi segreti del conto "test-1" con quelli di "K2" che l'exchange accetta
    Allora il conto "test-1" usa le credenziali "K2"
    E le credenziali "K1" non sono più conservate dalla piattaforma

  Scenario: Sostituzione con credenziali rifiutate
    Quando "anna" sostituisce i campi segreti del conto "test-1" con quelli di "K3" che l'exchange rifiuta
    Allora la sostituzione fallisce con il motivo "credenziali rifiutate dall'exchange"
    E il conto "test-1" continua a usare le credenziali "K1"

  Scenario: Il conto mostra i suoi campi pubblici
    Quando "anna" legge il conto "test-1"
    Allora il conto "test-1" mostra i campi pubblici di "K1"

  Scenario: Un campo pubblico inviato in una sostituzione è rifiutato
    Quando "anna" sostituisce le credenziali del conto "test-1" con tutte le credenziali di "K2" che l'exchange accetta
    Allora la sostituzione fallisce con il motivo "indirizzo del conto non si sostituisce: per cambiarlo rimuovi il conto e registrane uno nuovo"
    E il conto "test-1" continua a usare le credenziali "K1"

  Scenario: Un conto registrato senza campi pubblici conservati chiede tutte le credenziali
    Dato che il conto "test-1" non conserva i suoi campi pubblici
    Quando "anna" sostituisce le credenziali del conto "test-1" con tutte le credenziali di "K2" che l'exchange accetta
    Allora il conto "test-1" usa le credenziali "K2"
    E il conto "test-1" mostra i campi pubblici di "K2"

  Scenario: Le nuove credenziali appartengono a un altro conto dell'exchange
    Dato che il conto "test-1" non conserva i suoi campi pubblici
    Quando "anna" sostituisce le credenziali del conto "test-1" con credenziali valide di un diverso conto dell'exchange
    Allora la sostituzione fallisce con il motivo "le credenziali appartengono a un altro conto dell'exchange"
    E il conto "test-1" continua a usare le credenziali "K1"
