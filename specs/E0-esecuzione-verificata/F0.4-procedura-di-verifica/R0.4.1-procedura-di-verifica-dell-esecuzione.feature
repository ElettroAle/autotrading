# language: it
@R0.4.1
Funzionalità: R0.4.1 Procedura di verifica dell'esecuzione
  Come utente
  Voglio lanciare su un mio conto una procedura che apre, legge e chiude una posizione
  Perché sappia che lettura e invio degli ordini funzionano prima di affidare il conto a un flusso

  La procedura apre una posizione long su BTC con leva 2 e valore 12 USDC, legge lo stato, la chiude e legge di nuovo lo stato.
  Va lanciata prima di collegare un flusso e dopo ogni modifica all'esecuzione degli ordini.
  Nell'ambiente "prod" la procedura opera con fondi reali.
  La procedura non parte su un conto in cui BTC è un asset di un flusso attivo o in pausa: le sue esecuzioni
  cambierebbero la posizione che il flusso si aspetta e lo metterebbero in pausa (R1.6.2). I suoi ordini non
  appartengono a nessun flusso.

  Fuori ambito: verifica di stop loss e take profit, verifica su asset diversi da BTC.

  Contesto:
    Dato che "anna" ha il conto "test-1" su "Hyperliquid" con margine disponibile di almeno 12 USDC
    E che il conto "test-1" non ha posizioni su "BTC"

  Scenario: Procedura completata con successo
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora il passo "apertura long BTC leva 2" è riuscito
    E il passo "lettura dopo apertura" riporta una posizione long su "BTC" con leva 2
    E il passo "chiusura" è riuscito
    E il passo "lettura dopo chiusura" riporta nessuna posizione su "BTC"
    E l'esito complessivo della procedura è "superata"
    E l'esito riporta la commissione totale pagata e il profitto o la perdita realizzati

  Scenario: Lo stato letto coincide con quello dell'exchange
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora dopo ogni passo saldo e posizioni letti dalla piattaforma coincidono con quelli mostrati dall'exchange per il conto "test-1"

  Scenario: Procedura rifiutata con una posizione già aperta su BTC
    Dato che il conto "test-1" ha una posizione aperta su "BTC"
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora la procedura non parte con il motivo "posizione già aperta su BTC"
    E nessun ordine è inviato all'exchange

  Scenario: Procedura rifiutata su un asset di un flusso del conto
    Dato che sul conto "test-1" il flusso "alfa" attivo ha l'asset "BTC"
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora la procedura non parte con il motivo "BTC è un asset del flusso alfa"
    E nessun ordine è inviato all'exchange

  Scenario: Procedura rifiutata per margine insufficiente
    Dato che il conto "test-1" ha margine disponibile 5 USDC
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora la procedura non parte con il motivo "margine insufficiente: servono almeno 12 USDC"

  Scenario: Apertura fallita
    Dato che l'exchange rifiuta l'ordine di apertura
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora l'esito complessivo della procedura è "fallita al passo apertura"
    E l'esito riporta il messaggio originale dell'exchange
    E i passi successivi non sono eseguiti

  Scenario: Chiusura fallita dopo un'apertura riuscita
    Dato che l'exchange esegue l'apertura e rifiuta la chiusura
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora l'esito complessivo della procedura è "fallita al passo chiusura"
    E l'esito avverte che sul conto "test-1" resta aperta una posizione long su "BTC"

  Scenario: La procedura viene registrata
    Quando "anna" lancia la procedura di verifica sul conto "test-1"
    Allora la procedura è registrata con l'utente "anna", il conto "test-1", l'ambiente, l'istante, l'esito di ogni passo e l'esito complessivo
