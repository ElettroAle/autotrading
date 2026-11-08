# language: it
@R0.2.1
Funzionalità: R0.2.1 Registrazione di un conto di trading
  Come utente
  Voglio registrare nel mio spazio un conto di trading con le sue credenziali
  Perché la piattaforma possa leggerne lo stato e operare per mio conto

  Le credenziali sono quelle che l'exchange richiede (per Hyperliquid: indirizzo del conto e chiave dell'API wallet).
  L'utente le crea sull'exchange e le inserisce; la piattaforma non le genera.
  Quale rete dell'exchange si usa (test o reale) dipende dall'ambiente dell'installazione, non dal conto.

  Fuori ambito: generazione delle chiavi da parte della piattaforma, controllo della facoltà di prelievo delle credenziali, più exchange oltre Hyperliquid.

  Contesto:
    Dato che "anna" ha il ruolo "Utente"
    E che gli exchange supportati sono "Hyperliquid"

  Scenario: Registrazione riuscita con credenziali accettate dall'exchange
    Quando "anna" registra il conto "test-1" sull'exchange "Hyperliquid" con credenziali che l'exchange accetta
    Allora il conto "test-1" è salvato nello spazio di "anna"
    E il conto "test-1" riporta l'exchange "Hyperliquid"
    E il conto "test-1" riporta il saldo letto dall'exchange al momento della registrazione

  Scenario: Credenziali rifiutate dall'exchange
    Quando "anna" registra il conto "test-2" sull'exchange "Hyperliquid" con credenziali che l'exchange rifiuta
    Allora la registrazione del conto "test-2" fallisce con il motivo "credenziali rifiutate dall'exchange"
    E l'esito riporta il messaggio originale dell'exchange
    E il conto "test-2" non è salvato

  Scenario: Exchange non raggiungibile durante la registrazione
    Dato che l'exchange "Hyperliquid" non risponde
    Quando "anna" registra il conto "test-3" sull'exchange "Hyperliquid"
    Allora la registrazione del conto "test-3" fallisce con il motivo "exchange non raggiungibile, riprovare"
    E il conto "test-3" non è salvato

  Scenario: Exchange non supportato
    Quando "anna" registra il conto "test-4" sull'exchange "Binance"
    Allora la registrazione del conto "test-4" fallisce con il motivo "exchange non supportato"
    E l'esito elenca gli exchange supportati "Hyperliquid"

  Scenario: Nome del conto già usato nello stesso spazio
    Dato che "anna" ha già il conto "test-1"
    Quando "anna" registra un altro conto con il nome "test-1"
    Allora la registrazione fallisce con il motivo "nome del conto già in uso"

  Scenario: Lo stesso nome è ammesso in spazi diversi
    Dato che "bruno" ha il ruolo "Utente" e il conto "test-1"
    Quando "anna" registra il conto "test-1" con credenziali che l'exchange accetta
    Allora il conto "test-1" è salvato nello spazio di "anna"

  Schema dello scenario: Dati obbligatori mancanti
    Quando "anna" registra un conto senza "<dato>"
    Allora la registrazione fallisce con il motivo "<dato> obbligatorio"

    Esempi:
      | dato        |
      | nome        |
      | exchange    |
      | credenziali |
