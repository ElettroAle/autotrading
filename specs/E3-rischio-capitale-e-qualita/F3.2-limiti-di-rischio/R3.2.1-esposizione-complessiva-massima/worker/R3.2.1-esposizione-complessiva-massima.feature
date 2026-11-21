# language: it
@R3.2.1
Funzionalità: R3.2.1 Esposizione complessiva massima
  Come utente
  Voglio un limite alla somma delle posizioni aperte di un flusso
  Perché il flusso non impegna tutto il capitale anche se ogni operazione rispetta il suo limite

  Ogni flusso può avere due limiti di esposizione complessiva, facoltativi, in percentuale dei soldi del flusso
  (la stessa base dei limiti per operazione, R1.5.1): uno sul margine impegnato da tutte le posizioni aperte, uno sul
  valore di tutte le posizioni aperte. Ciascuno va da 0,1 a 1000.
  Un'apertura che porterebbe la somma oltre un limite viene ridotta al residuo; con entrambi i limiti vale il più
  restrittivo. Se il residuo è nullo l'apertura non viene eseguita (RF-18.03). Un residuo sotto l'importo minimo
  dell'exchange segue la regola del minimo (R1.5.4).
  Il limite complessivo si applica dopo quello per operazione. Le aperture dello stesso ciclo consumano il residuo
  nell'ordine in cui si eseguono.
  Ogni riduzione e ogni blocco si registra con la decisione originale, quella eseguita e il motivo (RF-18.10).
  Modificare i limiti crea una versione della configurazione (R1.1.3).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC", "ETH" e "SOL" e soldi del flusso per 1000 USDC

  Scenario: Apertura ridotta al residuo sul margine
    Dato che "alfa" ha esposizione complessiva massima del margine 30%
    E che "alfa" ha una posizione su "ETH" con margine 200 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" con margine 150 USDC
    Allora "alfa" apre la posizione su "BTC" con margine 100 USDC
    E il ciclo di "alfa" registra "apertura BTC ridotta da 150 a 100 USDC di margine: esposizione complessiva del margine al 30%"

  Scenario: Residuo nullo
    Dato che "alfa" ha esposizione complessiva massima del margine 30%
    E che "alfa" ha una posizione su "ETH" con margine 300 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" con margine 150 USDC
    Allora "alfa" non apre la posizione su "BTC"
    E il ciclo di "alfa" registra "apertura BTC non eseguita: esposizione complessiva del margine al 30% esaurita"

  Scenario: Apertura ridotta al residuo sul valore
    Dato che "alfa" ha esposizione complessiva massima del valore 100%
    E che "alfa" ha una posizione su "ETH" di valore 800 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" di valore 300 USDC
    Allora "alfa" apre la posizione su "BTC" di valore 200 USDC

  Scenario: Con entrambi i limiti vale il più restrittivo
    Dato che "alfa" ha esposizione complessiva massima del margine 30% e del valore 100%
    E che "alfa" ha una posizione su "ETH" con leva 2, margine 200 USDC e valore 400 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" con leva 2, margine 150 USDC e valore 300 USDC
    Allora "alfa" apre la posizione su "BTC" con margine 100 USDC e valore 200 USDC

  Scenario: Le aperture dello stesso ciclo consumano il residuo
    Dato che "alfa" ha esposizione complessiva massima del margine 30% e nessuna posizione aperta
    Quando l'agente di "alfa" decide nello stesso ciclo di aprire "BTC" con margine 200 USDC e "SOL" con margine 200 USDC
    Allora "alfa" apre la posizione su "BTC" con margine 200 USDC
    E "alfa" apre la posizione su "SOL" con margine 100 USDC

  Scenario: Apertura entro i limiti
    Dato che "alfa" ha esposizione complessiva massima del margine 30%
    E che "alfa" ha una posizione su "ETH" con margine 100 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" con margine 150 USDC
    Allora "alfa" apre la posizione su "BTC" con margine 150 USDC

  Scenario: Flusso senza limiti complessivi
    Dato che "alfa" non ha limiti di esposizione complessiva
    E che "alfa" ha una posizione su "ETH" con margine 300 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" con margine 150 USDC
    Allora "alfa" apre la posizione su "BTC" con margine 150 USDC

  Scenario: Residuo sotto l'importo minimo dell'exchange
    Dato che "alfa" ha esposizione complessiva massima del margine 30%
    E che "alfa" ha una posizione su "ETH" con margine 295 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" con margine 150 USDC
    Allora "alfa" non apre la posizione su "BTC"
    E il ciclo di "alfa" registra "valore sotto il minimo dell'exchange per BTC: 10 USDC"

  Scenario: Il limite complessivo si applica dopo quello per operazione
    Dato che "alfa" ha esposizione massima del margine per operazione 20% ed esposizione complessiva massima del margine 30%
    E che "alfa" ha una posizione su "ETH" con margine 200 USDC
    Quando l'agente di "alfa" decide di aprire long su "BTC" con margine 250 USDC
    Allora "alfa" apre la posizione su "BTC" con margine 100 USDC
    E il ciclo di "alfa" registra "apertura BTC ridotta da 200 a 100 USDC di margine: esposizione complessiva del margine al 30%"
