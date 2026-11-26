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
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC" e stop loss predefinito 5%

  Scenario: Flusso creato senza le impostazioni dello stop che segue
    Quando "anna" crea il flusso "beta" senza indicare distanza, attivazione, pareggio e opzione del massimo profitto
    Allora il flusso "beta" non ha distanza dello stop che segue, attivazione né pareggio
    E il flusso "beta" ha il massimo profitto raggiunto nel contesto dell'agente spento

  Scenario: Flussi già esistenti
    Dato che il flusso "alfa" esisteva prima dello stop che segue il prezzo
    Quando "anna" legge la configurazione di "alfa"
    Allora "alfa" non ha distanza dello stop che segue, attivazione né pareggio
    E la configurazione di "alfa" resta alla stessa versione

  Schema dello scenario: Distanza fuori dall'intervallo
    Quando "anna" imposta la distanza dello stop che segue di "alfa" a <valore>%
    Allora la modifica viene rifiutata con "la distanza dello stop che segue va da 0,1 a 50"

    Esempi:
      | valore |
      | 0      |
      | 0,05   |
      | 51     |

  Scenario: Attivazione senza distanza
    Quando "anna" imposta l'attivazione dello stop che segue di "alfa" a 3% senza distanza
    Allora la modifica viene rifiutata con "l'attivazione richiede la distanza dello stop che segue"

  Schema dello scenario: Percentuale non positiva
    Quando "anna" imposta <impostazione> di "alfa" a 0%
    Allora la modifica viene rifiutata con "<motivo>"

    Esempi:
      | impostazione                          | motivo                                              |
      | l'attivazione dello stop che segue    | l'attivazione dello stop che segue è maggiore di 0  |
      | il pareggio                           | il pareggio è maggiore di 0                         |

  Scenario: La modifica crea una versione
    Quando "anna" imposta la distanza dello stop che segue di "alfa" a 2%
    Allora "alfa" ha una nuova versione della configurazione con distanza dello stop che segue 2%

  Scenario: Impostazione tolta
    Dato che "alfa" ha distanza dello stop che segue 2%
    Quando "anna" toglie la distanza dello stop che segue di "alfa"
    Allora "alfa" ha una nuova versione della configurazione senza distanza dello stop che segue

  Scenario: Massimo profitto raggiunto nello stato
    Dato che "alfa" ha distanza dello stop che segue 2%
    E che "alfa" ha una posizione long su "BTC" di dimensione 0,01 con prezzo d'ingresso 60000
    E che il prezzo di "BTC" è salito a 63000 e poi sceso a 62000
    Quando "anna" legge lo stato di "alfa"
    Allora la posizione su "BTC" riporta massimo profitto raggiunto 30 USDC

  Scenario: Senza le impostazioni nessun massimo profitto
    Dato che "alfa" non ha distanza dello stop che segue né pareggio
    E che "alfa" ha una posizione long su "BTC" di dimensione 0,01 con prezzo d'ingresso 60000
    E che il prezzo di "BTC" è salito a 63000 e poi sceso a 62000
    Quando "anna" legge lo stato di "alfa"
    Allora la posizione su "BTC" non riporta nessun massimo profitto raggiunto
