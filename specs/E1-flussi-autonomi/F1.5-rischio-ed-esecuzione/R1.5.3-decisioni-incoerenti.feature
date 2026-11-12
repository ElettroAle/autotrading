# language: it
@R1.5.3
Funzionalità: R1.5.3 Decisioni incoerenti con lo stato del flusso
  Come utente
  Voglio che le decisioni incoerenti con lo stato del flusso siano bloccate
  Perché l'agente non agisca su posizioni o capitale che il flusso non ha

  Si bloccano: un'apertura su un asset su cui il flusso ha già una posizione aperta, una chiusura di una posizione
  che il flusso non ha, un'apertura il cui margine supera la liquidità disponibile del flusso dopo le riduzioni
  del rischio. Lo stato del flusso è quello letto all'inizio del ciclo.
  Una decisione bloccata non produce ordini e si registra con il motivo; le altre decisioni del ciclo proseguono.

  Fuori ambito: le decisioni non conformi al formato (R1.4.5), l'esposizione complessiva del flusso.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC, ETH", capitale allocato 1000 USDC e liquidità disponibile 40 USDC
    E che il flusso "alfa" ha una posizione long aperta su "BTC"

  Scenario: Apertura su un asset con posizione già aperta
    Dato che l'agente decide di aprire short su "BTC"
    Quando il rischio controlla la decisione
    Allora la decisione su "BTC" è bloccata con il motivo "posizione già aperta su BTC"
    E il ciclo non invia ordini su "BTC"

  Scenario: Chiusura di una posizione inesistente
    Dato che l'agente decide di chiudere su "ETH"
    Quando il rischio controlla la decisione
    Allora la decisione su "ETH" è bloccata con il motivo "nessuna posizione aperta su ETH"

  Scenario: Liquidità del flusso insufficiente
    Dato che l'agente decide di aprire long su "ETH" con un margine di 50 USDC dopo le riduzioni del rischio
    Quando il rischio controlla la decisione
    Allora la decisione su "ETH" è bloccata con il motivo "liquidità del flusso insufficiente: 40 USDC"

  Scenario: Le altre decisioni proseguono
    Dato che l'agente decide di aprire short su "BTC" e di mantenere su "ETH"
    Quando il rischio controlla le decisioni
    Allora la decisione su "BTC" è bloccata
    E la decisione su "ETH" è registrata come mantieni
