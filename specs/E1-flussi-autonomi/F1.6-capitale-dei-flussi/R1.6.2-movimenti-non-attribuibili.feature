# language: it
@R1.6.2
Funzionalità: R1.6.2 Posizioni e movimenti non attribuibili
  Come utente
  Voglio sapere quando sul conto c'è qualcosa che nessun flusso spiega
  Perché mi accorga di interventi manuali, liquidazioni o errori che falsano lo stato dei flussi

  A ogni ciclo, per il conto del flusso, si cerca ciò che non si attribuisce a nessun flusso:
  - una posizione aperta su un asset che nessun flusso del conto possiede;
  - una posizione di un flusso che la piattaforma considera aperta e che sull'exchange non c'è più;
  - un'esecuzione senza identificativo della piattaforma;
  - una variazione del saldo del conto che le esecuzioni dei flussi non spiegano (deposito, prelievo).
  Ogni caso si registra una sola volta con il conto, il tipo e i valori letti dall'exchange, e si notifica
  (R1.8.2). La piattaforma non tocca posizioni che non attribuisce. I flussi continuano a operare, tranne quello
  la cui posizione sull'exchange è diversa da quella attesa.
  Ogni flusso conosce la posizione che si aspetta su ogni suo asset dal registro delle operazioni (R1.6.1). Se
  all'inizio del ciclo, dopo la riconciliazione, la posizione del conto su un asset del flusso è diversa da quella
  attesa (per esempio l'utente ha comprato a mano sullo stesso asset), il ciclo non invia ordini, il flusso va in
  pausa con il motivo "posizione <asset> diversa da quella del flusso: attesa <A>, sul conto <B>" e arriva la
  notifica.
  Una posizione di un flusso chiusa fuori dalla piattaforma si registra nello storico del flusso come chiusa,
  con il motivo "chiusa fuori dalla piattaforma" e l'esito letto dall'exchange.

  Fuori ambito: la conferma dell'utente; la ripresa del flusso resta all'utente (R1.1.5).

  Contesto:
    Dato che "anna" ha il conto "test-1" con il solo flusso "alfa" con asset "BTC"

  Scenario: Posizione su un asset di nessun flusso
    Dato che sull'exchange il conto "test-1" ha una posizione aperta su "SOL"
    Quando il flusso "alfa" esegue un ciclo
    Allora è registrata per il conto "test-1" una posizione non attribuibile su "SOL"
    E la posizione su "SOL" resta aperta sull'exchange
    E il flusso "alfa" è nello stato "attivo"

  Scenario: Posizione di un flusso chiusa fuori dalla piattaforma
    Dato che il flusso "alfa" aveva una posizione aperta su "BTC"
    E che sull'exchange la posizione su "BTC" non c'è più
    Quando il flusso "alfa" esegue un ciclo
    Allora la posizione su "BTC" compare nello storico del flusso "alfa" come chiusa con il motivo "chiusa fuori dalla piattaforma"

  Scenario: Variazione del saldo non spiegata
    Dato che il saldo del conto "test-1" è aumentato di 200 USDC senza esecuzioni dei flussi
    Quando il flusso "alfa" esegue un ciclo
    Allora è registrata per il conto "test-1" una variazione del saldo non attribuibile di 200 USDC

  Scenario: Registrato una sola volta
    Dato che per il conto "test-1" è già registrata una posizione non attribuibile su "SOL"
    Quando il flusso "alfa" esegue un altro ciclo
    Allora per il conto "test-1" c'è una sola registrazione della posizione non attribuibile su "SOL"

  Scenario: Posizione del conto diversa da quella del flusso
    Dato che "anna" ha collegato Telegram
    E che il flusso "alfa" ha aperto 0,1 "BTC" con i propri ordini
    E che sull'exchange il conto "test-1" ha una posizione di 0,2 "BTC"
    Quando parte un ciclo del flusso "alfa" in cui l'agente apre "BTC"
    Allora nessun ordine è inviato
    E il flusso "alfa" è in pausa con il motivo "posizione BTC diversa da quella del flusso: attesa 0,1, sul conto 0,2"
    E "anna" riceve la notifica "alfa: in pausa, posizione BTC diversa da quella del flusso: attesa 0,1, sul conto 0,2"
