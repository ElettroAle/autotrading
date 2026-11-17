# language: it
@R3.3.1
Funzionalità: R3.3.1 Allarme sul saldo non spiegato
  Come utente
  Voglio un allarme che blocca le nuove aperture quando il saldo di un conto non torna
  Perché un intervento manuale, una liquidazione o un errore non lasciano i flussi a operare su numeri falsi

  A ogni ciclo, per il conto del flusso, la piattaforma confronta il saldo letto dall'exchange con il saldo atteso:
  l'ultimo saldo di riferimento più ciò che lo spiega, cioè esecuzioni, commissioni e funding dei flussi, e depositi e
  prelievi che l'exchange dichiara (R1.6.1). Ogni esecuzione e pagamento di funding dei flussi conta una sola volta:
  quello pubblicato dall'exchange dopo una lettura del saldo, con un istante non successivo a quella lettura, era già
  compreso nel saldo letto allora (Bug 506).
  Ogni conto ha una soglia di scostamento, in percentuale del saldo atteso, da 0,1 a 100, pari a 1 se non indicata.
  Uno scostamento oltre la soglia apre un allarme di riconciliazione sul conto (RF-13.07): si registrano saldo atteso,
  saldo letto e scostamento, l'utente viene avvisato, e le aperture di tutti i flussi del conto sono sospese finché
  l'utente non conferma di aver verificato. Chiusure e aggiornamenti del piano di uscita si eseguono; i cicli
  continuano.
  Uno scostamento entro la soglia si registra come variazione del saldo non spiegata (R1.6.2), senza allarme.
  Un deposito o un prelievo dichiarato dall'exchange è spiegato: non apre l'allarme e non è una variazione non
  spiegata.
  Con un allarme aperto non se ne apre un secondo sullo stesso conto.
  La conferma dell'utente chiude l'allarme, prende il saldo letto come nuovo riferimento, fa riprendere le aperture
  e si registra con data e ora.
  Fuori ambito: le posizioni non attribuibili, che restano solo segnalate (R1.6.2); lo stato nella dashboard (R3.3.2).

  Contesto:
    Dato che "anna" ha il conto "test-1" con i flussi attivi "alfa" e "beta" e soglia di scostamento 1%
    E che "anna" ha il conto "test-2" con il flusso attivo "gamma"
    E che il saldo atteso del conto "test-1" è 1000 USDC

  Scenario: Scostamento oltre la soglia
    Quando un ciclo di "alfa" legge dall'exchange il saldo 980 USDC
    Allora sul conto "test-1" c'è un allarme di riconciliazione con saldo atteso 1000 USDC, saldo letto 980 USDC e scostamento 2%
    E le aperture di "alfa" e "beta" sono sospese
    E "anna" riceve la notifica "test-1: allarme di riconciliazione, saldo 980 USDC invece di 1000 USDC"

  Scenario: Scostamento entro la soglia
    Quando un ciclo di "alfa" legge dall'exchange il saldo 995 USDC
    Allora sul conto "test-1" non c'è alcun allarme di riconciliazione
    E sul conto "test-1" è registrata una variazione del saldo non spiegata di -5 USDC

  Schema dello scenario: Deposito o prelievo dichiarato dall'exchange
    Dato che l'exchange dichiara sul conto "test-1" un <movimento> di <importo> USDC
    Quando un ciclo di "alfa" legge dall'exchange il saldo <saldo> USDC
    Allora sul conto "test-1" non c'è alcun allarme di riconciliazione
    E sul conto "test-1" non è registrata alcuna variazione del saldo non spiegata

    Esempi:
      | movimento | importo | saldo |
      | deposito  | 500     | 1500  |
      | prelievo  | 300     | 700   |

  Scenario: Apertura decisa durante l'allarme
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    Quando l'agente di "beta" decide di aprire long su "ETH"
    Allora "beta" non apre la posizione su "ETH"
    E il ciclo di "beta" registra "apertura ETH non eseguita: allarme di riconciliazione sul conto test-1"

  Scenario: Chiusura decisa durante l'allarme
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    E che "alfa" ha una posizione aperta su "BTC"
    Quando l'agente di "alfa" decide di chiudere la posizione su "BTC"
    Allora "alfa" chiude la posizione su "BTC"

  Scenario: Gli altri conti non sono coinvolti
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    Quando l'agente di "gamma" decide di aprire long su "SOL"
    Allora "gamma" apre la posizione su "SOL"

  Scenario: Un solo allarme aperto per conto
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    Quando il ciclo successivo di "beta" legge ancora il saldo 980 USDC
    Allora sul conto "test-1" c'è un solo allarme di riconciliazione
    E "anna" non riceve un'altra notifica di allarme

  Scenario: Conferma dell'utente
    Dato che sul conto "test-1" c'è un allarme di riconciliazione con saldo letto 980 USDC
    Quando "anna" conferma di aver verificato il conto "test-1"
    Allora l'allarme del conto "test-1" è chiuso
    E il saldo atteso del conto "test-1" è 980 USDC
    E le aperture di "alfa" e "beta" non sono sospese

  Scenario: Conferma senza allarme
    Quando "anna" conferma di aver verificato il conto "test-1"
    Allora il comando viene rifiutato con "il conto test-1 non ha un allarme di riconciliazione aperto"

  Scenario: Soglia del conto modificata
    Dato che "anna" imposta la soglia di scostamento del conto "test-1" a 3%
    Quando un ciclo di "alfa" legge dall'exchange il saldo 980 USDC
    Allora sul conto "test-1" non c'è alcun allarme di riconciliazione

  Schema dello scenario: Soglia fuori dall'intervallo
    Quando "anna" imposta la soglia di scostamento del conto "test-1" a <valore>%
    Allora la modifica viene rifiutata con "la soglia di scostamento va da 0,1 a 100"

    Esempi:
      | valore |
      | 0      |
      | 101    |

  Scenario: Funding pubblicato in ritardo contato una sola volta
    Dato che il conto "principale" ha una lettura precedente alle 10:00 con saldo di riferimento 1000
    E che alle 10:15 il registro scrive un pagamento di funding di 0,05 del flusso "alfa" avvenuto alle 09:59
    E che il saldo letto alle 10:15 è 1000
    Quando il conto si riconcilia
    Allora il saldo atteso è 1000
    E nessuna variazione del saldo non spiegata si registra

  Scenario: Esecuzione pubblicata in ritardo contata una sola volta
    Dato che il conto "principale" ha una lettura precedente alle 10:00 con saldo di riferimento 1000
    E che alle 10:15 il registro scrive un'esecuzione del flusso "alfa" delle 09:58 con PnL realizzato 2 e commissione 0,1
    E che il saldo letto alle 10:15 è 1000
    Quando il conto si riconcilia
    Allora nessuna variazione del saldo non spiegata si registra
