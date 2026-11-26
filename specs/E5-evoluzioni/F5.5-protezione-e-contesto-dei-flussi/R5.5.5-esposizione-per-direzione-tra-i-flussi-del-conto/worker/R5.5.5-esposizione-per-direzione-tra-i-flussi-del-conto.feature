# language: it
@R5.5.5
Funzionalità: R5.5.5 Esposizione nella stessa direzione tra i flussi del conto
  Come utente
  Voglio poter limitare quanto i flussi di un conto, sommati, sono esposti nella stessa direzione, e poter mostrare a un
  agente l'esposizione degli altri flussi del conto
  Perché i flussi di un conto non finiscano esposti tutti nella stessa direzione senza che nessuno lo sappia

  I limiti di esposizione valgono per il singolo flusso (R1.5.1, R3.2.1). Nessun limite e nessun dato riguarda l'insieme
  dei flussi di un conto: il 25 novembre 2026 quattro flussi dello stesso conto erano tutti short insieme, e nessun
  agente lo sapeva.

  Impostazioni, facoltative e vuote o spente di default. Con i default conto e flussi si comportano come oggi.
  - Sul conto, esposizione massima per direzione: percentuale maggiore di 0 del saldo del conto letto dall'exchange.
  - Sul flusso, esposizione del conto nel contesto dell'agente: opzione, spenta di default.

  Regole.
  - L'esposizione long del conto è la somma dei valori (dimensione per prezzo di mercato) delle posizioni long di tutti
    i flussi non archiviati del conto; lo stesso per lo short. Le due direzioni non si compensano. Le posizioni che
    nessun flusso spiega non contano.
  - Un'apertura è bloccata, col motivo, quando l'esposizione del conto in quella direzione più il valore dell'apertura
    supera il limite. Un'apertura che porta esattamente al limite passa. Non c'è riduzione dell'apertura, nemmeno con
    «porta al minimo».
  - Di un'inversione bloccata si esegue la sola chiusura della posizione aperta.
  - Il limite si imposta e si toglie dal conto, da API e dashboard.
  - Con l'opzione accesa, lo stato inviato all'agente riporta l'esposizione long e short degli altri flussi del conto,
    escluso il flusso stesso.

  Fuori ambito: limite sull'esposizione netta (long meno short), limite tra conti diversi, impostazione del limite dagli
  strumenti MCP.

  Contesto:
    Dato che "anna" ha il conto "principale" con saldo 2000 USDC ed esposizione massima per direzione 60%
    E che il flusso "beta" ha una posizione short su "BTC" di valore 800 USDC
    E che il flusso "gamma" ha una posizione short su "SOL" di valore 300 USDC e una posizione long su "DOGE" di valore 150 USDC
    E che il flusso "alfa" è attivo con asset "ETH" e senza posizioni

  Scenario: Apertura oltre il limite
    Quando l'agente di "alfa" decide di aprire short su "ETH" per un valore di 200 USDC
    Allora la decisione su "ETH" viene bloccata con "apertura short su ETH bloccata: esposizione short del conto 1300 USDC oltre il limite di 1200 USDC (60% del saldo 2000 USDC)"

  Scenario: Apertura che porta esattamente al limite
    Quando l'agente di "alfa" decide di aprire short su "ETH" per un valore di 100 USDC
    Allora la decisione su "ETH" viene approvata

  Scenario: L'altra direzione ha il suo conteggio
    Quando l'agente di "alfa" decide di aprire long su "ETH" per un valore di 200 USDC
    Allora la decisione su "ETH" viene approvata

  Scenario: Nessuna riduzione con porta al minimo
    Dato che "alfa" ha «porta al minimo» acceso
    Quando l'agente di "alfa" decide di aprire short su "ETH" per un valore di 200 USDC
    Allora la decisione su "ETH" viene bloccata con "apertura short su ETH bloccata: esposizione short del conto 1300 USDC oltre il limite di 1200 USDC (60% del saldo 2000 USDC)"

  Scenario: Inversione bloccata, resta la chiusura
    Dato che "alfa" ha una posizione long su "ETH" di valore 200 USDC
    Quando l'agente di "alfa" decide di invertire la posizione su "ETH" con un valore di 200 USDC
    Allora la posizione long di "alfa" su "ETH" viene chiusa
    E sull'exchange non c'è nessuna posizione di "alfa" su "ETH"

  Scenario: Conto senza limite
    Dato che il conto "principale" non ha esposizione massima per direzione
    Quando l'agente di "alfa" decide di aprire short su "ETH" per un valore di 200 USDC
    Allora la decisione su "ETH" viene approvata

  Schema dello scenario: Esposizione degli altri flussi nel contesto dell'agente
    Dato che "alfa" ha l'esposizione del conto nel contesto dell'agente <opzione>
    Quando parte il ciclo di "alfa"
    Allora lo stato del flusso inviato all'agente <esito> "altri flussi del conto: long 150 USDC, short 1100 USDC"

    Esempi:
      | opzione | esito       |
      | accesa  | riporta     |
      | spenta  | non riporta |
