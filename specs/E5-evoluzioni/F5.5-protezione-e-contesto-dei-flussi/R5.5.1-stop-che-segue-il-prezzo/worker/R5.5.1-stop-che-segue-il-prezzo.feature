# language: it
@R5.5.1
Funzionalità: R5.5.1 Stop che segue il prezzo
  Come utente
  Voglio che la piattaforma avvicini da sola lo stop loss al prezzo man mano che il prezzo va a favore della posizione
  Perché un profitto aperto resti protetto tra un ciclo e l'altro, senza aspettare il ciclo e senza dipendere dall'agente

  Oggi lo stop loss di una posizione si sposta solo quando l'agente decide «aggiorna» durante un ciclo (R3.1.3). Tra un
  ciclo e l'altro un profitto aperto non è protetto: il 25 novembre 2026 due flussi con ciclo di 4 ore hanno restituito
  circa 6 punti di rendimento in 4 ore e mezza.

  Impostazioni del flusso, tutte facoltative e vuote di default. Con tutte vuote il flusso si comporta come oggi.
  - Distanza dello stop che segue: percentuale da 0,1 a 50. Lo stop sta a quella distanza dal miglior prezzo che la
    posizione ha raggiunto (il più alto per un long, il più basso per uno short).
  - Attivazione dello stop che segue: percentuale maggiore di 0, ammessa solo insieme alla distanza. Lo stop comincia a
    seguire solo quando il prezzo è andato a favore di almeno quella percentuale dal prezzo d'ingresso. Vuota: segue
    dall'apertura.
  - Pareggio: percentuale maggiore di 0, indipendente dalle altre due. Quando il prezzo è andato a favore di almeno
    quella percentuale dal prezzo d'ingresso, lo stop va al prezzo d'ingresso.
  - Massimo profitto raggiunto nel contesto dell'agente: opzione, spenta di default. Ha effetto solo con la distanza o
    il pareggio impostati.

  Regole.
  - La piattaforma controlla il prezzo di ogni posizione dei flussi con una di queste impostazioni almeno una volta al
    minuto, indipendentemente dal ciclo.
  - Lo stop non si allontana mai dal prezzo: tra lo stop in vigore e lo stop calcolato vale quello più vicino al prezzo
    di mercato (il più alto per un long, il più basso per uno short).
  - L'agente può avvicinare lo stop con «aggiorna»; uno stop dell'agente più lontano dello stop calcolato dalla
    piattaforma viene riportato allo stop calcolato, e il ciclo lo registra.
  - Il miglior prezzo si conta dall'apertura della posizione; per una posizione già aperta quando l'impostazione entra
    in vigore, dal prezzo di mercato di quel momento.
  - Una modifica delle impostazioni vale anche per le posizioni già aperte, dal controllo successivo.
  - Una posizione chiusa dallo stop spostato entra nello storico con il motivo «stop loss», come oggi.
  - Il massimo profitto non realizzato raggiunto da una posizione aperta, nella valuta del conto, è visibile in API, MCP
    e dashboard solo per i flussi con la distanza o il pareggio impostati, perché solo le loro posizioni sono
    sorvegliate; all'agente arriva solo con l'opzione accesa. Per ogni altro flusso il valore è vuoto e la piattaforma
    non controlla nessun prezzo in più rispetto a oggi.

  Fuori ambito: obiettivo che segue il prezzo, chiusura parziale, impostazioni decise dall'agente per la singola
  posizione.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC", stop loss predefinito 5% e distanza dello stop che segue 2%
    E che "alfa" ha una posizione long su "BTC" con prezzo d'ingresso 60000 e stop loss a 57000

  Scenario: Lo stop segue dall'apertura
    Quando la piattaforma controlla il prezzo di "BTC" a 60000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 58800

  Scenario: Lo stop sale con il prezzo
    Quando il prezzo di "BTC" sale a 63000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 61740

  Scenario: Lo stop non torna indietro
    Dato che il prezzo di "BTC" è salito a 63000
    Quando il prezzo di "BTC" scende a 62000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 61740

  Scenario: Posizione short
    Dato che "alfa" ha invece una posizione short su "BTC" con prezzo d'ingresso 60000 e stop loss a 63000
    Quando il prezzo di "BTC" scende a 57000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 58140

  Schema dello scenario: Attivazione
    Dato che "alfa" ha attivazione dello stop che segue 3%
    Quando il prezzo di "BTC" sale a <prezzo>
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a <stop>

    Esempi:
      | prezzo | stop  |
      | 61000  | 57000 |
      | 61800  | 60564 |

  Schema dello scenario: Pareggio senza distanza
    Dato che "alfa" non ha distanza dello stop che segue e ha pareggio 1,5%
    Quando il prezzo di "BTC" sale a <prezzo>
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a <stop>

    Esempi:
      | prezzo | stop  |
      | 60600  | 57000 |
      | 60900  | 60000 |

  Scenario: Pareggio e distanza insieme, vale lo stop più vicino al prezzo
    Dato che "alfa" ha distanza dello stop che segue 2% e pareggio 1,5%
    Quando il prezzo di "BTC" sale a 60900
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 60000

  Scenario: Stop dell'agente più vicino al prezzo
    Dato che l'agente di "alfa" ha aggiornato lo stop su "BTC" a 59500
    Quando il prezzo di "BTC" sale a 60200
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 59500

  Scenario: Stop dell'agente più lontano dello stop che segue
    Dato che il prezzo di "BTC" è salito a 63000
    Quando l'agente di "alfa" decide di aggiornare lo stop su "BTC" a 58000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 61740
    E il ciclo di "alfa" registra "stop 58000 riportato a 61740: oltre lo stop che segue il prezzo"

  Scenario: Lo stop spostato torna all'agente
    Dato che il prezzo di "BTC" è salito a 63000
    Quando parte il ciclo successivo di "alfa"
    Allora lo stato del flusso inviato all'agente riporta per la posizione su "BTC" stop 61740

  Scenario: Spostamento rifiutato dall'exchange
    Dato che l'exchange rifiuta gli ordini di stop loss con "Trigger rejected"
    Quando il prezzo di "BTC" sale a 63000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 57000
    E il ciclo successivo di "alfa" registra "stop BTC non aggiornato, Trigger rejected"

  Scenario: Chiusura dallo stop spostato
    Dato che il prezzo di "BTC" è salito a 63000
    Quando l'exchange esegue l'ordine di stop loss a 61740
    Allora lo storico delle posizioni chiuse di "alfa" contiene "BTC" con motivo "stop loss"

  Scenario: Impostazione entrata in vigore con la posizione già aperta
    Dato che "alfa" non aveva distanza dello stop che segue quando il prezzo di "BTC" è salito a 64000
    E che il prezzo di "BTC" è 62000
    Quando "anna" imposta la distanza dello stop che segue di "alfa" a 2%
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 60760

  Scenario: Senza impostazioni lo stop non si muove
    Dato che "alfa" non ha distanza dello stop che segue né pareggio
    Quando il prezzo di "BTC" sale a 63000
    Allora sull'exchange l'unico ordine di stop loss di "alfa" su "BTC" è a 57000
    E la piattaforma non sorveglia il prezzo di "BTC" per "alfa" tra un ciclo e l'altro

  Schema dello scenario: Massimo profitto raggiunto nel contesto dell'agente
    Dato che la posizione di "alfa" su "BTC" ha dimensione 0,01
    E che il prezzo di "BTC" è salito a 63000 e poi sceso a 62000
    E che "alfa" ha il massimo profitto raggiunto nel contesto dell'agente <opzione>
    Quando parte il ciclo successivo di "alfa"
    Allora lo stato del flusso inviato all'agente <esito> per la posizione su "BTC" il massimo profitto raggiunto 30 USDC

    Esempi:
      | opzione | esito       |
      | acceso  | riporta     |
      | spento  | non riporta |
