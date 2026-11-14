# language: it
@R2.3.9
Funzionalità: R2.3.9 Credenziali secondo il fornitore
  Come utente
  Voglio che la registrazione di un conto o di una chiave IA chieda i dati che quell'exchange o quel fornitore richiede
  Perché exchange e fornitori diversi chiedono credenziali diverse

  Ogni adapter dichiara i campi delle proprie credenziali (nome, etichetta, segreto o no); l'API li espone e la
  dashboard genera il modulo. I campi segreti non si mostrano in chiaro.

  Fuori ambito: exchange oltre Hyperliquid.

  Contesto:
    Dato che "anna" è nella pagina dei conti

  Scenario: La registrazione di un conto chiede i dati che l'exchange richiede
    Quando "anna" sceglie l'exchange "Hyperliquid" per registrare un conto
    Allora la registrazione chiede "indirizzo del conto" e "chiave dell'API wallet"
    E la chiave non è mostrata in chiaro

  Scenario: Dato obbligatorio dell'exchange mancante
    Quando "anna" registra un conto "Hyperliquid" senza la chiave dell'API wallet
    Allora la registrazione fallisce con il motivo "chiave dell'API wallet obbligatorio"

  Scenario: La chiave di un fornitore IA chiede i dati che il fornitore richiede
    Quando "anna" sceglie il fornitore "openrouter" per registrare una chiave
    Allora la registrazione chiede i dati che "openrouter" richiede
    E i dati segreti non sono mostrati in chiaro
