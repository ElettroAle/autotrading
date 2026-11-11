# language: it
@R1.5.2 @wip
Funzionalità: R1.5.2 Leva massima del flusso
  Come utente
  Voglio fissare la leva massima di un flusso
  Perché l'agente non apra posizioni con una leva più alta di quella che accetto

  Un'apertura con leva superiore alla leva massima del flusso si riduce alla leva massima e si esegue, mantenendo
  il margine impegnato. La riduzione si registra con la decisione originale, quella eseguita e il motivo.
  La leva massima del flusso non supera quella che l'exchange ammette per l'asset: se la supera, vale il massimo
  dell'exchange, con lo stesso trattamento.
  La riduzione della leva precede il controllo dell'esposizione (R1.5.1).

  Fuori ambito: leve massime diverse per asset.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con leva massima 5 e capitale allocato 1000 USDC

  Scenario: Leva ridotta al massimo del flusso
    Dato che l'agente decide di aprire long su "BTC" con quota 0,05 e leva 10
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita impegna 50 USDC di margine con leva 5
    E il ciclo registra la riduzione della leva da 10 a 5 con il motivo "leva oltre il massimo del flusso: 5"

  Scenario: Leva ridotta al massimo dell'exchange
    Dato che il flusso "alfa" ha leva massima 50
    E che l'exchange ammette per "BTC" una leva massima di 40
    E che l'agente decide di aprire long su "BTC" con quota 0,05 e leva 50
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita ha leva 40
    E il ciclo registra la riduzione della leva da 50 a 40 con il motivo "leva oltre il massimo dell'exchange per BTC: 40"

  Scenario: Leva entro il massimo
    Dato che l'agente decide di aprire long su "BTC" con quota 0,05 e leva 3
    Quando il rischio controlla la decisione
    Allora l'apertura eseguita ha leva 3
