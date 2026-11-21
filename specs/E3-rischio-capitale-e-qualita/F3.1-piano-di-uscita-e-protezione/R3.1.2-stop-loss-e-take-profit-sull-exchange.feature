# language: it
@R3.1.2
Funzionalità: R3.1.2 Stop loss e take profit sull'exchange
  Come utente
  Voglio che ogni posizione aperta da un flusso abbia stop loss e take profit attivi sull'exchange
  Perché la posizione resta protetta tra un ciclo e l'altro, anche se la piattaforma è ferma

  Ogni flusso ha uno stop loss predefinito, obbligatorio: una percentuale di distanza dal prezzo d'ingresso, tra
  0,1 e 50, pari a 5 se non indicata. I flussi che esistono già ricevono 5. Il take profit predefinito è facoltativo:
  una percentuale maggiore di 0 dal prezzo d'ingresso, oppure assente. Modificarli crea una versione della
  configurazione (R1.1.3) e vale per le aperture successive.
  A ogni apertura la piattaforma piazza sull'exchange, sull'intera posizione, l'ordine di stop loss e, se c'è un
  obiettivo, l'ordine di take profit. Valgono i livelli del piano di uscita dell'agente (R3.1.1); dove mancano, i
  predefiniti del flusso calcolati sul prezzo d'ingresso reale (RF-18.06).
  Uno stop dell'agente più lontano dal prezzo d'ingresso dello stop predefinito si riporta allo stop predefinito, e
  il ciclo lo registra.
  Se l'exchange rifiuta l'ordine di stop loss, la posizione appena aperta si chiude subito e il ciclo ne registra il
  motivo. Se rifiuta solo il take profit, la posizione resta con il suo stop e il rifiuto si registra.
  Quando l'exchange esegue lo stop loss o il take profit, la chiusura è del flusso: entra nello storico delle
  posizioni chiuse con il motivo "stop loss" o "take profit" e con l'esito letto dall'exchange.
  Quando la posizione si chiude, per qualunque motivo, gli ordini di protezione rimasti si annullano.
  Una posizione aperta prima che il flusso avesse lo stop predefinito riceve lo stop loss al ciclo successivo.

  Fuori ambito: lo spostamento dei livelli di una posizione aperta (R3.1.3); lo stop del flusso, che continua a
  chiudere le posizioni (R1.1.5); le notifiche di stop loss e take profit (R3.5.1).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC", stop loss predefinito 5% e nessun take profit predefinito

  Schema dello scenario: Stop loss predefinito all'apertura
    Quando "alfa" apre <direzione> su "BTC" al prezzo d'ingresso 60000 senza piano di uscita
    Allora sull'exchange c'è un ordine di stop loss a <stop> sull'intera posizione di "alfa" su "BTC"
    E sull'exchange non c'è un ordine di take profit per quella posizione

    Esempi:
      | direzione | stop  |
      | long      | 57000 |
      | short     | 63000 |

  Scenario: Take profit predefinito del flusso
    Dato che "alfa" ha take profit predefinito 10%
    Quando "alfa" apre long su "BTC" al prezzo d'ingresso 60000 senza piano di uscita
    Allora sull'exchange c'è un ordine di take profit a 66000 sull'intera posizione di "alfa" su "BTC"

  Scenario: Livelli indicati dall'agente
    Quando "alfa" apre long su "BTC" al prezzo d'ingresso 60000 con obiettivo 63000 e stop 58500
    Allora sull'exchange c'è un ordine di stop loss a 58500 sull'intera posizione di "alfa" su "BTC"
    E sull'exchange c'è un ordine di take profit a 63000 sull'intera posizione di "alfa" su "BTC"

  Scenario: Stop dell'agente oltre lo stop predefinito
    Quando "alfa" apre long su "BTC" al prezzo d'ingresso 60000 con stop 55000
    Allora sull'exchange c'è un ordine di stop loss a 57000 sull'intera posizione di "alfa" su "BTC"
    E il ciclo di "alfa" registra "stop 55000 riportato a 57000: oltre lo stop predefinito del 5%"

  Scenario: Stop loss rifiutato dall'exchange
    Dato che l'exchange rifiuta gli ordini di stop loss con "Trigger rejected"
    Quando "alfa" apre long su "BTC"
    Allora la posizione di "alfa" su "BTC" viene chiusa subito
    E il ciclo di "alfa" registra "posizione BTC chiusa: stop loss non piazzato, Trigger rejected"

  Scenario: Take profit rifiutato dall'exchange
    Dato che l'exchange rifiuta gli ordini di take profit con "Trigger rejected"
    Quando "alfa" apre long su "BTC" al prezzo d'ingresso 60000 con obiettivo 63000
    Allora la posizione di "alfa" su "BTC" resta aperta con lo stop loss a 57000
    E il ciclo di "alfa" registra "take profit non piazzato su BTC, Trigger rejected"

  Schema dello scenario: Chiusura eseguita dall'exchange
    Dato che "alfa" ha una posizione long su "BTC" con stop loss a 57000 e take profit a 63000
    Quando l'exchange esegue l'ordine di <ordine> con PnL <pnl> USDC
    Allora lo storico delle posizioni chiuse di "alfa" contiene "BTC" con motivo "<ordine>" e PnL <pnl> USDC
    E sull'exchange non resta alcun ordine di protezione di "alfa" su "BTC"

    Esempi:
      | ordine      | pnl   |
      | stop loss   | -5,10 |
      | take profit | 4,90  |

  Scenario: La chiusura decisa dall'agente annulla gli ordini di protezione
    Dato che "alfa" ha una posizione long su "BTC" con stop loss a 57000 e take profit a 63000
    Quando l'agente di "alfa" decide di chiudere la posizione su "BTC"
    Allora sull'exchange non resta alcun ordine di protezione di "alfa" su "BTC"

  Schema dello scenario: Stop loss predefinito fuori dall'intervallo
    Quando "anna" imposta lo stop loss predefinito di "alfa" a <valore>%
    Allora la modifica viene rifiutata con "lo stop loss predefinito va da 0,1 a 50"

    Esempi:
      | valore |
      | 0      |
      | 0,05   |
      | 51     |

  Scenario: Take profit predefinito non positivo
    Quando "anna" imposta il take profit predefinito di "alfa" a 0%
    Allora la modifica viene rifiutata con "il take profit predefinito è maggiore di 0"

  Scenario: Flusso creato senza indicare lo stop loss predefinito
    Quando "anna" crea il flusso "beta" senza indicare lo stop loss predefinito
    Allora il flusso "beta" ha stop loss predefinito 5%

  Scenario: La modifica dei predefiniti crea una versione
    Quando "anna" imposta lo stop loss predefinito di "alfa" a 3%
    Allora "alfa" ha una nuova versione della configurazione con stop loss predefinito 3%

  Scenario: Posizione aperta prima dello stop predefinito
    Dato che "alfa" ha una posizione long su "BTC" con prezzo d'ingresso 60000 e nessun ordine di stop loss sull'exchange
    Quando parte il ciclo successivo di "alfa"
    Allora sull'exchange c'è un ordine di stop loss a 57000 sull'intera posizione di "alfa" su "BTC"

  Scenario: La modifica dei predefiniti vale per le aperture successive
    Dato che "anna" ha impostato lo stop loss predefinito di "alfa" a 3%
    Quando "alfa" apre long su "BTC" al prezzo d'ingresso 60000 senza piano di uscita
    Allora sull'exchange c'è un ordine di stop loss a 58200 sull'intera posizione di "alfa" su "BTC"

  @pipeline
  Scenario: I flussi già esistenti ricevono lo stop loss predefinito
    Dato che "anna" aveva il flusso "alfa" salvato prima degli stop loss predefiniti
    Quando la piattaforma passa alla versione con gli stop loss predefiniti
    Allora "alfa" ha lo stop loss predefinito 5% e nessun take profit predefinito
    E la configurazione di "alfa" resta alla stessa versione
