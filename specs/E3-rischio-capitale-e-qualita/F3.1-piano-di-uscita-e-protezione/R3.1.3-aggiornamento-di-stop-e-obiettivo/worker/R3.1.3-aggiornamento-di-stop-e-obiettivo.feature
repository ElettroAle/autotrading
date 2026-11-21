# language: it
@R3.1.3
Funzionalità: R3.1.3 Aggiornamento di stop e obiettivo di una posizione aperta
  Come utente
  Voglio che l'agente possa spostare stop e obiettivo di una posizione già aperta
  Perché può proteggere i guadagni maturati senza chiudere la posizione

  Per un asset con una posizione aperta l'agente può decidere di aggiornare il piano di uscita: nuovo stop, nuovo
  obiettivo, nuova condizione di invalidazione, o togliere l'obiettivo. La piattaforma sostituisce gli ordini di
  protezione sull'exchange, così che resti un solo stop loss e al più un take profit per posizione.
  Lo stop loss non si toglie mai e non può stare più lontano dal prezzo d'ingresso dello stop predefinito del flusso
  (R3.1.2): uno stop più lontano si riporta allo stop predefinito e il ciclo lo registra.
  Un livello incoerente con il prezzo di mercato dell'exchange del conto (R3.1.1) si scarta, resta quello in vigore e
  il ciclo ne registra il motivo.
  Se l'exchange rifiuta la sostituzione, resta attivo l'ordine precedente e il ciclo registra il rifiuto.
  Il ciclo registra il livello prima e dopo. Il piano aggiornato è quello che torna all'agente e che la dashboard
  mostra (R3.1.1).
  Un aggiornamento su un asset senza posizione aperta è una decisione incoerente con lo stato del flusso (R1.5.3).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC" e stop loss predefinito 5%
    E che "alfa" ha una posizione long su "BTC" con prezzo d'ingresso 60000, stop loss a 57000 e take profit a 66000
    E che il prezzo di mercato di "BTC" sull'exchange del conto è 64000

  Scenario: Stop avvicinato al prezzo
    Quando l'agente di "alfa" decide di aggiornare lo stop su "BTC" a 62000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 62000
    E il ciclo di "alfa" registra "stop BTC da 57000 a 62000"

  Scenario: Stop più lontano dello stop predefinito
    Quando l'agente di "alfa" decide di aggiornare lo stop su "BTC" a 55000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 57000
    E il ciclo di "alfa" registra "stop 55000 riportato a 57000: oltre lo stop predefinito del 5%"

  Scenario: Stop incoerente con il prezzo di mercato
    Quando l'agente di "alfa" decide di aggiornare lo stop su "BTC" a 65000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 57000
    E il ciclo di "alfa" registra "stop 65000 scartato: incoerente con long al prezzo 64000"

  Scenario: Nuovo obiettivo
    Quando l'agente di "alfa" decide di aggiornare l'obiettivo su "BTC" a 68000
    Allora sull'exchange l'unico ordine di take profit di "alfa" su "BTC" è a 68000

  Scenario: Obiettivo tolto
    Quando l'agente di "alfa" decide di togliere l'obiettivo su "BTC"
    Allora sull'exchange non c'è un ordine di take profit di "alfa" su "BTC"
    E sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 57000

  Scenario: Sostituzione rifiutata dall'exchange
    Dato che l'exchange rifiuta gli ordini di stop loss con "Trigger rejected"
    Quando l'agente di "alfa" decide di aggiornare lo stop su "BTC" a 62000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 57000
    E il ciclo di "alfa" registra "stop BTC non aggiornato, Trigger rejected"

  Scenario: Il piano aggiornato torna all'agente
    Dato che l'agente di "alfa" ha aggiornato lo stop su "BTC" a 62000
    Quando parte il ciclo successivo di "alfa"
    Allora lo stato del flusso inviato all'agente riporta per la posizione su "BTC" stop 62000

  Scenario: Aggiornamento senza posizione aperta
    Dato che "alfa" ha anche l'asset "ETH" senza posizione aperta
    Quando l'agente di "alfa" decide di aggiornare lo stop su "ETH" a 3000
    Allora la decisione su "ETH" viene bloccata con "nessuna posizione aperta su ETH"
