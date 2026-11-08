# language: it
@R0.2.2
Funzionalità: R0.2.2 Lettura dello stato del conto
  Come utente
  Voglio vedere lo stato aggiornato di un mio conto
  Perché sappia saldo, margine disponibile e posizioni aperte in questo momento

  Lo stato è letto dall'exchange alla richiesta, non da una copia salvata.

  Fuori ambito: storico dello stato, ripartizione del saldo tra flussi (arriva con la contabilità dei flussi).

  Contesto:
    Dato che "anna" ha il conto "test-1" su "Hyperliquid"

  Scenario: Stato di un conto senza posizioni
    Dato che sull'exchange il conto "test-1" ha saldo 1000 USDC e nessuna posizione aperta
    Quando "anna" chiede lo stato del conto "test-1"
    Allora lo stato riporta il saldo 1000 USDC
    E lo stato riporta il margine disponibile 1000 USDC
    E lo stato riporta nessuna posizione aperta
    E lo stato riporta l'istante della lettura

  Scenario: Stato di un conto con una posizione aperta
    Dato che sull'exchange il conto "test-1" ha una posizione long su "BTC" con leva 2
    Quando "anna" chiede lo stato del conto "test-1"
    Allora lo stato riporta per "BTC" la direzione "long"
    E lo stato riporta per "BTC" la dimensione
    E lo stato riporta per "BTC" la leva 2
    E lo stato riporta per "BTC" il prezzo di ingresso
    E lo stato riporta per "BTC" il profitto o la perdita non realizzati
    E lo stato riporta per "BTC" il prezzo di liquidazione

  Scenario: Exchange non raggiungibile durante la lettura
    Dato che l'exchange "Hyperliquid" non risponde
    Quando "anna" chiede lo stato del conto "test-1"
    Allora la richiesta fallisce con il motivo "exchange non raggiungibile, riprovare"
    E l'esito non riporta valori di saldo

  Scenario: Credenziali non più accettate dall'exchange
    Dato che l'exchange rifiuta ora le credenziali del conto "test-1"
    Quando "anna" chiede lo stato del conto "test-1"
    Allora la richiesta fallisce con il motivo "credenziali rifiutate dall'exchange"
    E l'esito riporta il messaggio originale dell'exchange
