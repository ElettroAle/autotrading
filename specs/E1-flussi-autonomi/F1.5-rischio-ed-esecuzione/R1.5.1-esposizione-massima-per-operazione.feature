# language: it
@R1.5.1 @wip
Funzionalità: R1.5.1 Esposizione massima per operazione
  Come utente
  Voglio limitare quanto un'apertura può impegnare del capitale del flusso
  Perché un errore dell'agente non metta a rischio una parte eccessiva del capitale

  Il flusso ha due limiti di esposizione per operazione, entrambi in percentuale del capitale allocato al flusso:
  sul margine impegnato (prima della leva) e sul valore della posizione (con la leva). Almeno uno dei due è
  configurato; se lo sono entrambi, vale quello che porta alla posizione più piccola.
  Un'apertura oltre il limite non si scarta: si riduce al limite e si esegue. La riduzione si registra con la
  decisione originale, quella eseguita e il motivo.

  Fuori ambito: l'esposizione complessiva del flusso, la perdita massima.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con capitale allocato 1000 USDC e liquidità disponibile 1000 USDC

  Scenario: Riduzione al limite sul margine
    Dato che il flusso "alfa" ha esposizione massima del margine 5% e nessun limite sul valore
    E che l'agente decide di aprire long su "BTC" con quota 0,2 e leva 2
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita impegna 50 USDC di margine con leva 2
    E il ciclo registra la riduzione da 200 a 50 USDC di margine con il motivo "esposizione del margine oltre il 5%"

  Scenario: Riduzione al limite sul valore
    Dato che il flusso "alfa" ha esposizione massima del valore 10% e nessun limite sul margine
    E che l'agente decide di aprire long su "BTC" con quota 0,1 e leva 3
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita ha valore 100 USDC con leva 3
    E il ciclo registra la riduzione da 300 a 100 USDC di valore con il motivo "esposizione del valore oltre il 10%"

  Scenario: Con entrambi i limiti vale il più restrittivo
    Dato che il flusso "alfa" ha esposizione massima del margine 5% e del valore 8%
    E che l'agente decide di aprire long su "BTC" con quota 0,05 e leva 4
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita ha valore 80 USDC con leva 4

  Scenario: Apertura entro i limiti
    Dato che il flusso "alfa" ha esposizione massima del margine 5%
    E che l'agente decide di aprire long su "BTC" con quota 0,03 e leva 2
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita impegna 30 USDC di margine con leva 2
    E il ciclo non registra riduzioni
