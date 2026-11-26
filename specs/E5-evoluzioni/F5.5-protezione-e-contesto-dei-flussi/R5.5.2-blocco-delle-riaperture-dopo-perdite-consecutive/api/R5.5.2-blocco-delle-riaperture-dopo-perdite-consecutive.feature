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
    Dato che "anna" ha il flusso "alfa" attivo con asset "NEAR" e "SUI"

  Scenario: Flusso creato senza il limite
    Quando "anna" crea il flusso "beta" senza indicare perdite consecutive massime, finestra e durata del blocco
    Allora il flusso "beta" non ha il blocco delle riaperture

  Scenario: Flussi già esistenti
    Dato che il flusso "alfa" esisteva prima del blocco delle riaperture
    Quando "anna" legge la configurazione di "alfa"
    Allora "alfa" non ha il blocco delle riaperture
    E la configurazione di "alfa" resta alla stessa versione

  Scenario: Le tre impostazioni vanno insieme
    Quando "anna" imposta le perdite consecutive massime di "alfa" a 2 senza finestra e senza durata del blocco
    Allora la modifica viene rifiutata con "perdite consecutive massime, finestra delle perdite e durata del blocco si impostano insieme"

  Schema dello scenario: Valore sotto il minimo
    Quando "anna" imposta per "alfa" perdite consecutive massime <perdite>, finestra <finestra> ore e durata del blocco <durata> minuti
    Allora la modifica viene rifiutata con "<motivo>"

    Esempi:
      | perdite | finestra | durata | motivo                                             |
      | 0       | 24       | 120    | le perdite consecutive massime sono almeno 1       |
      | 2       | 0        | 120    | la finestra delle perdite è di almeno 1 ora        |
      | 2       | 24       | 0      | la durata del blocco è di almeno 1 minuto          |

  Scenario: La modifica crea una versione
    Quando "anna" imposta per "alfa" perdite consecutive massime 2, finestra 24 ore e durata del blocco 120 minuti
    Allora "alfa" ha una nuova versione della configurazione con perdite consecutive massime 2, finestra 24 ore e durata del blocco 120 minuti

  Scenario: Ambito non indicato
    Quando "anna" imposta per "alfa" perdite consecutive massime 2, finestra 24 ore e durata del blocco 120 minuti senza ambito
    Allora "alfa" ha il blocco delle riaperture con ambito del conteggio "asset"

  Scenario: Ambito non ammesso
    Quando "anna" imposta per "alfa" perdite consecutive massime 2, finestra 24 ore, durata del blocco 120 minuti e ambito del conteggio "conto"
    Allora la modifica viene rifiutata con "l'ambito del conteggio è asset oppure flusso"

  Scenario: Ambito senza le altre impostazioni
    Quando "anna" imposta l'ambito del conteggio di "alfa" a "flusso" senza perdite consecutive massime, finestra e durata del blocco
    Allora la modifica viene rifiutata con "perdite consecutive massime, finestra delle perdite e durata del blocco si impostano insieme"

  Scenario: Limite tolto
    Dato che "alfa" ha perdite consecutive massime 2, finestra 24 ore e durata del blocco 120 minuti
    Quando "anna" toglie il blocco delle riaperture di "alfa"
    Allora "alfa" ha una nuova versione della configurazione senza il blocco delle riaperture
