# language: it
@R3.1.4
Funzionalità: R3.1.4 Confidenza e soglia minima
  Come utente
  Voglio che ogni decisione dichiari quanto l'agente ne è convinto e poter fissare una soglia minima
  Perché il flusso non apre posizioni su decisioni deboli

  Ogni decisione dell'agente contiene un punteggio di confidenza, un intero da 0 a 100 (RF-17.06). Una decisione
  senza confidenza o con un valore fuori dall'intervallo è una risposta non conforme (R1.4.5).
  La confidenza si registra con la decisione e compare nel dettaglio del ciclo.
  Ogni flusso può avere una confidenza minima, un intero da 0 a 100, assente se non indicata. Un'apertura con
  confidenza sotto la minima non viene eseguita e il ciclo ne registra il motivo (RF-18.07). La soglia vale solo per
  le aperture: chiusure e aggiornamenti del piano di uscita si eseguono sempre, perché riducono il rischio.
  Modificare la confidenza minima crea una versione della configurazione (R1.1.3).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC" e confidenza minima 60

  Scenario: Confidenza registrata con la decisione
    Quando l'agente di "alfa" decide di aprire long su "BTC" con confidenza 75
    Allora la decisione registrata di "alfa" su "BTC" ha confidenza 75

  Scenario: Apertura sotto la confidenza minima
    Quando l'agente di "alfa" decide di aprire long su "BTC" con confidenza 40
    Allora "alfa" non apre la posizione su "BTC"
    E il ciclo di "alfa" registra "apertura BTC non eseguita: confidenza 40 sotto la minima 60"

  Scenario: Apertura pari alla confidenza minima
    Quando l'agente di "alfa" decide di aprire long su "BTC" con confidenza 60
    Allora "alfa" apre la posizione su "BTC"

  Scenario: La chiusura non dipende dalla confidenza
    Dato che "alfa" ha una posizione aperta su "BTC"
    Quando l'agente di "alfa" decide di chiudere la posizione su "BTC" con confidenza 20
    Allora "alfa" chiude la posizione su "BTC"

  Scenario: Flusso senza confidenza minima
    Dato che "anna" ha il flusso "beta" attivo con asset "BTC" senza confidenza minima
    Quando l'agente di "beta" decide di aprire long su "BTC" con confidenza 5
    Allora "beta" apre la posizione su "BTC"

  Schema dello scenario: Confidenza minima fuori dall'intervallo
    Quando "anna" imposta la confidenza minima di "alfa" a <valore>
    Allora la modifica viene rifiutata con "la confidenza minima va da 0 a 100"

    Esempi:
      | valore |
      | -1     |
      | 101    |

  Scenario: Decisione senza confidenza
    Quando l'agente di "alfa" risponde con una decisione su "BTC" senza confidenza
    Allora la decisione su "BTC" viene scartata come non conforme

  Scenario: Confidenza nel dettaglio del ciclo
    Dato che l'agente di "alfa" ha deciso di aprire long su "BTC" con confidenza 75
    Quando "anna" apre nella dashboard il dettaglio di quel ciclo
    Allora la decisione su "BTC" mostra confidenza 75
