# language: it
@R0.3.2
Funzionalità: R0.3.2 Chiusura manuale di una posizione
  Come utente
  Voglio chiudere in qualunque momento una posizione aperta su un mio conto
  Perché possa sempre togliere esposizione senza aspettare un flusso

  La chiusura è totale. L'utente non può aprire posizioni a mano.

  Fuori ambito: chiusura parziale, chiusura di tutte le posizioni con un comando (chiusura di emergenza), apertura manuale.

  Contesto:
    Dato che "anna" ha il conto "test-1" su "Hyperliquid"

  Scenario: Chiusura di una posizione aperta
    Dato che il conto "test-1" ha una posizione long su "BTC"
    Quando "anna" chiude la posizione su "BTC" del conto "test-1"
    Allora sull'exchange il conto "test-1" non ha posizioni su "BTC"
    E l'esito riporta il prezzo medio di chiusura
    E l'esito riporta il profitto o la perdita realizzati
    E l'esito riporta la commissione pagata
    E la chiusura è registrata con il motivo "comando manuale" e l'utente "anna"

  Scenario: Chiusura di una posizione inesistente
    Dato che il conto "test-1" non ha posizioni su "ETH"
    Quando "anna" chiude la posizione su "ETH" del conto "test-1"
    Allora la richiesta fallisce con il motivo "nessuna posizione aperta su ETH"
    E nessun ordine è inviato all'exchange

  Scenario: L'utente non può aprire posizioni a mano
    Quando "anna" chiede di aprire una posizione su "BTC" del conto "test-1"
    Allora la richiesta è respinta con il motivo "apertura manuale non consentita"
    E nessun ordine è inviato all'exchange
