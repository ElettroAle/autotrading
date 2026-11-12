# language: it
@R1.5.4
Funzionalità: R1.5.4 Apertura sotto l'importo minimo dell'exchange
  Come utente
  Voglio che un'apertura sotto l'importo minimo dell'exchange sia trattata in modo prevedibile
  Perché non dipenda da un rifiuto dell'exchange né da un arrotondamento casuale

  Il flusso ha l'opzione "porta al minimo", disattivata per impostazione predefinita.
  Disattivata: un'apertura il cui valore, dopo le riduzioni del rischio, è sotto il minimo dell'exchange non si
  invia e si registra come bloccata.
  Attivata: l'apertura sale al minimo dell'exchange, purché il minimo rispetti i limiti di esposizione (R1.5.1)
  e la liquidità del flusso (R1.5.3); altrimenti si blocca. L'aumento si registra con il motivo.

  Fuori ambito: l'arrotondamento della dimensione ai passi dell'exchange, già coperto dall'apertura di una
  posizione (R0.3.1).

  Contesto:
    Dato che l'exchange ammette per "BTC" un valore minimo di apertura di 10 USDC
    E che "anna" ha il flusso "alfa" con capitale allocato 1000 USDC, esposizione massima del valore 5% e liquidità disponibile 1000 USDC

  Scenario: Apertura sotto il minimo non eseguita per impostazione predefinita
    Dato che l'agente decide un'apertura su "BTC" di valore 6 USDC
    Quando il rischio controlla la decisione
    Allora la decisione su "BTC" è bloccata con il motivo "valore sotto il minimo dell'exchange per BTC: 10 USDC"
    E il ciclo non invia ordini su "BTC"

  Scenario: Apertura portata al minimo
    Dato che il flusso "alfa" ha l'opzione "porta al minimo" attivata
    E che l'agente decide un'apertura su "BTC" di valore 6 USDC
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita su "BTC" ha valore 10 USDC
    E il ciclo registra l'aumento da 6 a 10 USDC con il motivo "portata al minimo dell'exchange"

  Scenario: Minimo oltre il limite di esposizione
    Dato che il flusso "alfa" ha l'opzione "porta al minimo" attivata ed esposizione massima del valore 0,5%
    E che l'agente decide un'apertura su "BTC" di valore 6 USDC
    Quando il rischio controlla la decisione
    Allora la decisione su "BTC" è bloccata con il motivo "minimo dell'exchange oltre il limite di esposizione"
