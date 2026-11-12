# language: it
@R1.5.5
Funzionalità: R1.5.5 Esecuzione delle decisioni del flusso
  Come utente
  Voglio che le decisioni approvate dal rischio diventino ordini sul conto del flusso, con l'esito reale
  Perché il flusso operi davvero e ogni ordine sia riconducibile al flusso e al ciclo che l'hanno generato

  Le decisioni approvate si eseguono sul conto del flusso: prima le chiusure, poi le aperture.
  Ogni ordine porta l'identificativo della piattaforma (R0.3.1) ed è collegato al flusso, al ciclo e alla
  decisione. Dopo ogni ordine si legge dall'exchange l'esito effettivo (prezzo, quantità, commissione) e si
  registra l'esito reale, non quello atteso (R0.3.4).
  Un ordine rifiutato dall'exchange si registra con il messaggio originale (R0.3.3) e non ferma gli altri ordini
  del ciclo. Un exchange che non risponde fa fallire il ciclo (R1.2.3).
  La quantità di un'apertura si arrotonda per difetto al passo dell'asset; se così il valore scendesse sotto il
  minimo dell'exchange, si arrotonda per eccesso di un passo, perché un'apertura approvata non sia rifiutata.

  Fuori ambito: stop loss e take profit sull'exchange, chiusure parziali.

  Contesto:
    Dato che "anna" ha il flusso "alfa" sul conto "test-1" con una posizione long aperta su "ETH"

  Scenario: Chiusure prima delle aperture
    Dato che il rischio approva la chiusura su "ETH" e un'apertura long su "BTC"
    Quando il flusso "alfa" esegue gli ordini del ciclo "c-1"
    Allora l'ordine di chiusura su "ETH" è inviato prima dell'ordine di apertura su "BTC"

  Scenario: Ordine collegato a flusso, ciclo e decisione
    Dato che il rischio approva un'apertura long su "BTC"
    Quando il flusso "alfa" esegue gli ordini del ciclo "c-1"
    Allora l'ordine su "BTC" porta l'identificativo della piattaforma
    E l'ordine su "BTC" è collegato al flusso "alfa", al ciclo "c-1" e alla decisione su "BTC"

  Scenario: Esito reale registrato
    Dato che il rischio approva un'apertura long su "BTC" al prezzo atteso di 100000
    E che l'exchange esegue l'ordine a 100050 con commissione 0,04 USDC
    Quando il flusso "alfa" esegue gli ordini del ciclo "c-1"
    Allora il ciclo registra per "BTC" il prezzo eseguito 100050 e la commissione 0,04 USDC

  Scenario: Ordine rifiutato non ferma gli altri
    Dato che il rischio approva la chiusura su "ETH" e un'apertura long su "BTC"
    E che l'exchange rifiuta la chiusura su "ETH" con il messaggio "Order rejected"
    Quando il flusso "alfa" esegue gli ordini del ciclo "c-1"
    Allora il ciclo registra per "ETH" l'ordine rifiutato con il messaggio "Order rejected"
    E l'ordine di apertura su "BTC" è inviato

  Scenario: Arrotondamento che non scende sotto il minimo dell'exchange
    Dato che l'exchange ammette per "BTC" un valore minimo di ordine di 10 USDC al prezzo di 60123 con 5 decimali di quantità
    E che il rischio approva un'apertura long su "BTC" di valore 10 USDC
    Quando il flusso "alfa" esegue gli ordini del ciclo "c-1"
    Allora l'ordine su "BTC" è inviato con quantità 0,00017
