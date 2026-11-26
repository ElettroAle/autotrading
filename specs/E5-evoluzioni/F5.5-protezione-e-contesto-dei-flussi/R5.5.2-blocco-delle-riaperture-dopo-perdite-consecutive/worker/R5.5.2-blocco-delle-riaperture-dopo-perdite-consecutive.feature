# language: it
@R5.5.2
Funzionalità: R5.5.2 Blocco delle riaperture dopo perdite consecutive
  Come utente
  Voglio un limite di rischio facoltativo che, dopo un numero di perdite consecutive nella stessa direzione, blocchi per
  un tempo le aperture in quella direzione, contando e bloccando per singolo asset o per tutto il flusso, come scelgo io
  Perché l'agente non riapra subito la direzione in cui ha appena perso

  Un agente può riaprire più volte la stessa direzione sullo stesso asset subito dopo averci perso, anche con la memoria
  attiva: il 25 novembre 2026 un flusso ha aperto cinque short consecutivi in perdita. La perdita giornaliera massima
  (R3.2.2) ferma tutto il flusso, non la sola direzione che sta perdendo.

  Dato misurato. I cinque short del 25 novembre 2026 erano su due asset: un conteggio per singolo asset con 2 perdite e
  120 minuti di blocco non ne avrebbe fermato nessuno. Per questo l'ambito del conteggio è un'impostazione.

  Impostazioni del flusso, vuote di default; si impostano tutte e tre insieme o nessuna. Con le tre vuote il flusso si
  comporta come oggi.
  - Perdite consecutive massime: intero da 1 in su.
  - Finestra delle perdite: ore, intero da 1 in su.
  - Durata del blocco: minuti, intero da 1 in su.
  - Ambito del conteggio: «asset» oppure «flusso»; ammesso solo insieme alle altre tre, «asset» se non indicato.

  Regole.
  - Quando l'agente decide un'apertura su un asset in una direzione, si guardano le posizioni del flusso su quell'asset
    e in quella direzione chiuse dentro la finestra, dalla più recente all'indietro. Si contano finché sono in perdita
    (PnL al netto delle commissioni sotto zero): una posizione chiusa in utile o in pari interrompe il conteggio.
  - Se il conteggio raggiunge le perdite consecutive massime e dall'ultima di quelle chiusure è passato meno della
    durata del blocco, l'apertura è bloccata con il motivo, e il ciclo la registra. Il blocco finisce da solo allo
    scadere.
  - Con ambito «asset» l'altra direzione sullo stesso asset e gli altri asset del flusso non sono toccati.
  - Con ambito «flusso» si guardano le posizioni chiuse del flusso in quella direzione su tutti gli asset, e il blocco
    ferma le aperture in quella direzione su ogni asset del flusso; l'altra direzione non è toccata.
  - Di un'inversione bloccata si esegue la sola chiusura della posizione aperta.
  - Finché un blocco è in corso lo stato inviato all'agente lo riporta, e la dashboard lo mostra.

  Fuori ambito: ripresa manuale del blocco, notifica del blocco, conteggio tra flussi diversi.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "NEAR" e "SUI", perdite consecutive massime 2, finestra 24 ore e durata del blocco 120 minuti
    E che "alfa" ha chiuso in perdita due posizioni short su "NEAR", alle 13:00 e alle 13:30 di oggi

  Scenario: Apertura bloccata dopo due perdite consecutive
    Quando alle 14:00 l'agente di "alfa" decide di aprire short su "NEAR"
    Allora la decisione su "NEAR" viene bloccata con "apertura short su NEAR bloccata: 2 perdite consecutive, riaperture short su NEAR ferme fino alle 15:30"
    E sull'exchange non c'è nessuna posizione di "alfa" su "NEAR"

  Schema dello scenario: L'altra direzione e gli altri asset non sono toccati
    Quando alle 14:00 l'agente di "alfa" decide di aprire <direzione> su "<asset>"
    Allora la decisione su "<asset>" viene approvata

    Esempi:
      | direzione | asset |
      | long      | NEAR  |
      | short     | SUI   |

  Schema dello scenario: Ambito flusso, le perdite si contano su tutti gli asset
    Dato che "alfa" ha ambito del conteggio "flusso"
    E che "alfa" ha invece chiuso in perdita una posizione short su "NEAR" alle 13:00 e una posizione short su "SUI" alle 13:30
    Quando alle 14:00 l'agente di "alfa" decide di aprire short su "<asset>"
    Allora la decisione su "<asset>" viene bloccata con "apertura short su <asset> bloccata: 2 perdite consecutive short nel flusso, riaperture short ferme fino alle 15:30"

    Esempi:
      | asset |
      | NEAR  |
      | SUI   |

  Scenario: Ambito flusso, l'altra direzione non è toccata
    Dato che "alfa" ha ambito del conteggio "flusso"
    E che "alfa" ha invece chiuso in perdita una posizione short su "NEAR" alle 13:00 e una posizione short su "SUI" alle 13:30
    Quando alle 14:00 l'agente di "alfa" decide di aprire long su "NEAR"
    Allora la decisione su "NEAR" viene approvata

  Scenario: Ambito asset, perdite su asset diversi non si sommano
    Dato che "alfa" ha invece chiuso in perdita una posizione short su "NEAR" alle 13:00 e una posizione short su "SUI" alle 13:30
    Quando alle 14:00 l'agente di "alfa" decide di aprire short su "NEAR"
    Allora la decisione su "NEAR" viene approvata

  Scenario: Blocco scaduto
    Quando alle 15:31 l'agente di "alfa" decide di aprire short su "NEAR"
    Allora la decisione su "NEAR" viene approvata

  Scenario: Una terza perdita dopo il blocco lo fa ripartire
    Dato che "alfa" ha aperto short su "NEAR" alle 15:31 e la posizione si è chiusa in perdita alle 16:00
    Quando alle 16:10 l'agente di "alfa" decide di aprire short su "NEAR"
    Allora la decisione su "NEAR" viene bloccata con "apertura short su NEAR bloccata: 3 perdite consecutive, riaperture short su NEAR ferme fino alle 18:00"

  Schema dello scenario: Una chiusura non in perdita interrompe il conteggio
    Dato che "alfa" ha invece chiuso tre posizioni short su "NEAR": in perdita alle 12:00, <esito> alle 13:00 e in perdita alle 13:30
    Quando alle 14:00 l'agente di "alfa" decide di aprire short su "NEAR"
    Allora la decisione su "NEAR" viene approvata

    Esempi:
      | esito    |
      | in utile |
      | in pari  |

  Scenario: Perdita fuori dalla finestra
    Dato che "alfa" ha invece chiuso in perdita due posizioni short su "NEAR", 30 ore fa e 1 ora fa
    Quando l'agente di "alfa" decide di aprire short su "NEAR"
    Allora la decisione su "NEAR" viene approvata

  Scenario: Inversione bloccata, resta la chiusura
    Dato che "alfa" ha una posizione long su "NEAR"
    Quando alle 14:00 l'agente di "alfa" decide di invertire la posizione su "NEAR"
    Allora la posizione long di "alfa" su "NEAR" viene chiusa
    E sull'exchange non c'è nessuna posizione di "alfa" su "NEAR"
    E il ciclo di "alfa" registra "apertura short su NEAR bloccata: 2 perdite consecutive, riaperture short su NEAR ferme fino alle 15:30"

  Scenario: Il blocco in corso arriva all'agente
    Quando alle 14:00 parte il ciclo di "alfa"
    Allora lo stato del flusso inviato all'agente riporta "riaperture short su NEAR ferme fino alle 15:30: 2 perdite consecutive"

  Scenario: Senza il limite nessun blocco
    Dato che "alfa" non ha il blocco delle riaperture
    Quando alle 14:00 l'agente di "alfa" decide di aprire short su "NEAR"
    Allora la decisione su "NEAR" viene approvata
    E lo stato del flusso inviato all'agente non riporta riaperture ferme
