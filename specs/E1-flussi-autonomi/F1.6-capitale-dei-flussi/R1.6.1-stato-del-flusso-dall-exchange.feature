# language: it
@R1.6.1
Funzionalità: R1.6.1 Stato del flusso attribuito dall'exchange
  Come utente
  Voglio che lo stato di ogni flusso sia ricavato da ciò che l'exchange mostra
  Perché capitale, posizioni e risultati di un flusso siano veri e non si mescolino con quelli degli altri flussi

  L'exchange conosce solo i totali del conto: la piattaforma non tiene una liquidità propria, ripartisce ciò che
  legge dall'exchange.
  - Le posizioni si leggono dall'exchange: una posizione appartiene al flusso del conto che ha quell'asset (R1.1.2).
  - Le esecuzioni (prezzo, quantità, commissione, PnL realizzato) si leggono dall'exchange e si attribuiscono al
    flusso tramite l'identificativo dell'ordine.
  - La liquidità disponibile del flusso è: capitale allocato, più PnL realizzato delle sue esecuzioni, meno le
    sue commissioni, meno il margine impegnato nelle sue posizioni aperte.
  - Il valore complessivo del flusso è la liquidità disponibile più margine e PnL non realizzato delle sue
    posizioni. Il rendimento dall'avvio è il valore complessivo rispetto al capitale allocato.
  Una variazione del capitale allocato (R1.1.7) cambia il capitale di riferimento del rendimento dal momento
  della variazione.
  Con un solo flusso sul conto e tutto il saldo allocato, i valori del flusso coincidono con quelli del conto.
  Il ciclo del flusso usa lo stesso stato: l'agente riceve questi valori e il controllo del rischio blocca
  un'apertura il cui margine supera la liquidità disponibile (R1.5.3). Nel ciclo la liquidità disponibile non
  supera mai il margine libero del conto e non scende sotto zero.

  Fuori ambito: incasso dei profitti, rendimento corretto per incassi e prelievi.

  Contesto:
    Dato che "anna" ha il conto "test-1" con i flussi "alfa" (asset "BTC", capitale allocato 500 USDC) e "beta" (asset "ETH", capitale allocato 300 USDC)

  Scenario: Posizioni attribuite per asset
    Dato che sull'exchange il conto "test-1" ha posizioni aperte su "BTC" e su "ETH"
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha la sola posizione su "BTC"

  Scenario: Liquidità calcolata dalle esecuzioni
    Dato che le esecuzioni del flusso "alfa" hanno PnL realizzato 40 USDC e commissioni 2 USDC
    E che il flusso "alfa" ha 100 USDC impegnati come margine in posizioni aperte
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha liquidità disponibile 438 USDC

  Scenario: Valore complessivo e rendimento
    Dato che il flusso "alfa" ha liquidità disponibile 438 USDC e una posizione con margine 100 USDC e PnL non realizzato 12 USDC
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha valore complessivo 550 USDC
    E il flusso "alfa" ha rendimento dall'avvio del 10%

  Scenario: Le esecuzioni di un flusso non toccano l'altro
    Dato che le esecuzioni del flusso "alfa" hanno PnL realizzato 40 USDC
    Quando "anna" consulta lo stato del flusso "beta"
    Allora il flusso "beta" ha liquidità disponibile 300 USDC

  Scenario: Un solo flusso coincide con il conto
    Dato che "anna" ha il conto "test-2" con saldo 1000 USDC e il solo flusso "gamma" con capitale allocato 1000 USDC e nessuna operazione
    Quando "anna" consulta lo stato del flusso "gamma"
    Allora il flusso "gamma" ha liquidità disponibile 1000 USDC, uguale al margine disponibile del conto "test-2"

  Scenario: Il ciclo usa lo stato attribuito del flusso
    Dato che le esecuzioni del flusso "alfa" hanno PnL realizzato -100 USDC e commissioni 2 USDC
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC" con quota 0,8 e leva 1
    Allora l'agente riceve per il flusso "alfa" liquidità disponibile 398 USDC, valore complessivo 398 USDC e rendimento dall'avvio del -20,40%
    E l'apertura del flusso "alfa" è bloccata con il motivo "liquidità del flusso insufficiente: 398 USDC"

  Scenario: La liquidità del ciclo non supera il margine libero del conto
    Dato che sull'exchange il margine libero del conto "test-1" è 200 USDC
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC" con quota 0,5 e leva 1
    Allora l'agente riceve per il flusso "alfa" liquidità disponibile 200 USDC
    E l'apertura del flusso "alfa" è bloccata con il motivo "liquidità del flusso insufficiente: 200 USDC"
