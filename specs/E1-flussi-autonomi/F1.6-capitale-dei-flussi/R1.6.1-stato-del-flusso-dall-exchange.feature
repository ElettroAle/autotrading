# language: it
@R1.6.1
Funzionalità: R1.6.1 Stato del flusso attribuito dall'exchange
  Come utente
  Voglio che lo stato di ogni flusso sia ricavato da ciò che l'exchange mostra
  Perché capitale, posizioni e risultati di un flusso siano veri e non si mescolino con quelli degli altri flussi

  L'exchange conosce solo i totali del conto: la piattaforma non tiene una liquidità propria, ripartisce ciò che
  legge dall'exchange.
  - Le posizioni si leggono dall'exchange: una posizione appartiene al flusso del conto che ha quell'asset (R1.1.2).
  - Le esecuzioni (prezzo, quantità, commissione, PnL realizzato) e i pagamenti di funding si leggono
    dall'exchange a ogni ciclo, solo quelli nuovi, e la piattaforma li registra una sola volta nel proprio
    registro delle operazioni, che conserva l'intero storico anche quando l'exchange non lo mostra più.
  - Un'esecuzione è del flusso il cui ordine l'ha prodotta; un ordine della piattaforma senza flusso (comando
    manuale, stop) è del flusso che ha l'asset. Senza un ordine della piattaforma sono del flusso dell'asset solo
    la liquidazione e la chiusura esatta della posizione che il flusso si aspetta; ogni altra esecuzione non è di
    nessun flusso. Il funding è del flusso che ha la posizione sull'asset quando è pagato.
  - Per ogni flusso la piattaforma tiene i totali di PnL realizzato, commissioni, funding e posizione attesa per
    asset, aggiornati con le sole righe nuove: lo stato si legge dai totali, mai sommando lo storico, e i totali
    si possono sempre ricalcolare dallo storico.
  - Se l'exchange non conserva più tutte le esecuzioni avvenute dall'ultima lettura, il registro sarebbe
    incompleto: tutti i flussi del conto vanno in pausa con il motivo e arriva la notifica.
  - La liquidità disponibile del flusso è: capitale allocato, più PnL realizzato e funding delle sue esecuzioni,
    meno le sue commissioni, meno il margine impegnato nelle sue posizioni aperte.
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

  Scenario: Lo storico del flusso resta intero quando l'exchange non lo mostra più
    Dato che le esecuzioni del flusso "alfa" hanno PnL realizzato 40 USDC e commissioni 2 USDC
    E che l'exchange non mostra più le esecuzioni del conto "test-1"
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha liquidità disponibile 538 USDC

  Scenario: Un'esecuzione letta di nuovo si conta una volta sola
    Dato che le esecuzioni del flusso "alfa" hanno PnL realizzato 40 USDC e commissioni 2 USDC
    E che il ciclo successivo legge di nuovo le stesse esecuzioni del conto "test-1"
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha liquidità disponibile 538 USDC

  Scenario: La liquidazione della posizione del flusso è del flusso
    Dato che il flusso "alfa" ha aperto 2 "BTC" con i propri ordini
    E che l'exchange liquida la posizione "BTC" con PnL realizzato -80 USDC
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha liquidità disponibile 420 USDC

  Schema dello scenario: Solo la chiusura esatta della posizione del flusso fuori dalla piattaforma è del flusso
    Dato che il flusso "alfa" ha aperto 2 "BTC" con i propri ordini
    E che sull'exchange una vendita di <quantità> "BTC" fuori dalla piattaforma realizza PnL <pnl> USDC
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha liquidità disponibile <liquidità> USDC

    Esempi:
      | quantità | pnl | liquidità |
      | 2        | -10 | 490       |
      | 1        | -5  | 500       |

  Scenario: Il funding della posizione del flusso è del flusso
    Dato che il flusso "alfa" ha aperto 1 "BTC" con i propri ordini
    E che sull'exchange la posizione "BTC" paga un funding di -3 USDC
    Quando "anna" consulta lo stato del flusso "alfa"
    Allora il flusso "alfa" ha liquidità disponibile 497 USDC

  Scenario: I totali del flusso si ricalcolano dallo storico
    Dato che il flusso "alfa" ha aperto 1 "BTC" con i propri ordini
    E che le esecuzioni del flusso "alfa" hanno PnL realizzato 40 USDC e commissioni 2 USDC
    E che sull'exchange la posizione "BTC" paga un funding di -3 USDC
    Quando si ricalcolano dallo storico i totali del flusso "alfa"
    Allora i totali ricalcolati del flusso "alfa" coincidono con quelli che legge il ciclo

  Scenario: Un registro incompleto mette in pausa i flussi del conto
    Dato che il registro del conto "test-1" è aggiornato a un ciclo precedente
    E che dall'ultimo ciclo il conto "test-1" ha più esecuzioni di quante l'exchange ne conservi
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC" con quota 0,1 e leva 1
    Allora nessun ordine è inviato
    E i flussi "alfa" e "beta" sono in pausa con il motivo "registro delle esecuzioni incompleto"
