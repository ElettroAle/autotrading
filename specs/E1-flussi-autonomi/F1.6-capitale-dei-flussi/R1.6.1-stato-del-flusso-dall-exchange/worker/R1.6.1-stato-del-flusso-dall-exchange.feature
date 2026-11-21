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
    registro delle operazioni, che conserva l'intero storico anche quando l'exchange non lo mostra più. Un'esecuzione
    o un funding che l'exchange pubblica in ritardo, fino a un'ora dopo il suo istante, entra comunque nel registro.
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
  Il ciclo del flusso usa lo stesso stato: l'agente riceve questi valori, il controllo del rischio misura le quote
  sui soldi del flusso (R1.5.1) e blocca un'apertura il cui margine supera la liquidità disponibile (R1.5.3). Nel ciclo la liquidità disponibile non
  supera mai il margine libero del conto e non scende sotto zero.

  Il registro delle operazioni si consulta: per un flusso, le sue esecuzioni e i suoi pagamenti di funding; per un
  conto, le operazioni che non sono di nessun flusso. Le operazioni vanno dalla più recente, 50 per pagina; la
  pagina successiva parte dall'ultima operazione vista. Si filtrano per asset e per periodo (inizio compreso, fine
  esclusa).

  Fuori ambito: incasso dei profitti, rendimento corretto per incassi e prelievi.

  Contesto:
    Dato che "anna" ha il conto "test-1" con i flussi "alfa" (asset "BTC", capitale allocato 500 USDC) e "beta" (asset "ETH", capitale allocato 300 USDC)

  Scenario: Il ciclo usa lo stato attribuito del flusso
    Dato che le esecuzioni del flusso "alfa" hanno PnL realizzato -100 USDC e commissioni 2 USDC
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC" con quota 0,8 e leva 1
    Allora l'agente riceve per il flusso "alfa" liquidità disponibile 398 USDC, valore complessivo 398 USDC e rendimento dall'avvio del -20,40%
    E l'apertura del flusso "alfa" è approvata per un valore di 318,4 USDC

  Scenario: La liquidità del ciclo non supera il margine libero del conto
    Dato che sull'exchange il margine libero del conto "test-1" è 200 USDC
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC" con quota 0,5 e leva 1
    Allora l'agente riceve per il flusso "alfa" liquidità disponibile 200 USDC
    E l'apertura del flusso "alfa" è bloccata con il motivo "liquidità del flusso insufficiente: 200 USDC"

  Scenario: La liquidità del ciclo non scende sotto zero
    Dato che le esecuzioni del flusso "alfa" hanno PnL realizzato -600 USDC e commissioni 0 USDC
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC" con quota 0,1 e leva 1
    Allora l'agente riceve per il flusso "alfa" liquidità disponibile 0 USDC
    E nessun ordine è inviato

  Scenario: Un registro incompleto mette in pausa i flussi del conto
    Dato che il registro del conto "test-1" è aggiornato a un ciclo precedente
    E che dall'ultimo ciclo il conto "test-1" ha più esecuzioni di quante l'exchange ne conservi
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC" con quota 0,1 e leva 1
    Allora nessun ordine è inviato
    E i flussi "alfa" e "beta" sono in pausa con il motivo "registro delle esecuzioni incompleto"
