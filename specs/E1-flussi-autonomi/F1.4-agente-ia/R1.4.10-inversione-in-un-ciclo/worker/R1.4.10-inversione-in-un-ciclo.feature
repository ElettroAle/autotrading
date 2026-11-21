# language: it
@R1.4.10
Funzionalità: R1.4.10 Inversione della posizione in un ciclo
  Come utente
  Voglio che l'agente possa girare una posizione da long a short, o da short a long, in un solo ciclo
  Perché il flusso non resti fuori dal mercato per un ciclo intero quando la direzione cambia

  Alle azioni di R1.4.4 si aggiunge "inverti", ammessa solo su un asset con una posizione aperta del flusso: chiude
  tutta la posizione e, nello stesso ciclo, ne apre una nella direzione opposta. La direzione nuova è sempre l'opposta
  di quella aperta: il campo direzione della decisione si ignora. Quota, leva, obiettivo, stop, invalidazione e
  confidenza sono quelli di un'apertura.
  Resta al massimo una posizione per asset e la chiusura resta totale. Prima si esegue la chiusura; l'apertura si
  controlla come ogni apertura (leva, esposizione, confidenza minima, aperture sospese, importo minimo) sui soldi e
  sulla liquidità del flusso dopo la chiusura eseguita, e riceve stop e obiettivo come in R3.1.2.
  Se l'apertura è bloccata, la chiusura si esegue comunque: l'agente ha deciso di uscire da quella direzione. Se la
  chiusura non è eseguita dall'exchange, l'apertura non si invia. Il ciclo registra chiusura e apertura, ciascuna col
  suo esito, e la posizione chiusa entra nello storico col motivo "inversione".

  Fuori ambito: incremento di una posizione aperta e chiusura parziale (R5.4.1).

  Contesto:
    Dato che "anna" ha il flusso attivo "alfa" con asset "BTC, ETH" e soldi del flusso 100 USDC
    E che "alfa" ha una posizione short aperta su "BTC"

  Scenario: Inversione eseguita
    Dato che l'agente risponde inverti su "BTC" con quota 0,2 e leva 3
    Quando il flusso "alfa" esegue un ciclo
    Allora la posizione short su "BTC" è chiusa per intero
    E "alfa" ha una posizione long aperta su "BTC" con leva 3
    E il ciclo registra la chiusura e l'apertura, ciascuna col suo esito
    E la posizione chiusa è nello storico col motivo "inversione"

  Scenario: L'apertura si misura sui soldi dopo la chiusura
    Dato che la chiusura della short su "BTC" realizza una perdita di 5 USDC
    E che l'agente risponde inverti su "BTC" con quota 0,2 e leva 2
    Quando il flusso "alfa" esegue un ciclo
    Allora la posizione long su "BTC" impegna 19 USDC di margine

  Scenario: Apertura bloccata, chiusura eseguita
    Dato che "alfa" ha le aperture sospese per perdita massima
    E che l'agente risponde inverti su "BTC" con quota 0,2 e leva 3
    Quando il flusso "alfa" esegue un ciclo
    Allora la posizione short su "BTC" è chiusa per intero
    E "alfa" non ha posizioni aperte su "BTC"
    E il ciclo registra l'apertura bloccata col motivo della sospensione

  Scenario: Chiusura non eseguita
    Dato che l'exchange non esegue la chiusura della short su "BTC"
    E che l'agente risponde inverti su "BTC" con quota 0,2 e leva 3
    Quando il flusso "alfa" esegue un ciclo
    Allora nessuna apertura è inviata all'exchange
    E "alfa" ha ancora la posizione short su "BTC"

  Scenario: Inversione senza posizione aperta
    Dato che l'agente risponde inverti su "ETH" con quota 0,2 e leva 3
    Quando il flusso "alfa" esegue un ciclo
    Allora la decisione su "ETH" è bloccata con il motivo "nessuna posizione da invertire"

  Scenario: Il campo direzione si ignora
    Dato che l'agente risponde inverti su "BTC" con direzione short, quota 0,2 e leva 3
    Quando il flusso "alfa" esegue un ciclo
    Allora "alfa" ha una posizione long aperta su "BTC"

  Scenario: L'apertura dell'inversione riceve stop e obiettivo sull'exchange
    Dato che l'agente risponde inverti su "BTC" con quota 0,2, leva 3, obiettivo 110000 e stop 97000
    Quando il flusso "alfa" esegue un ciclo
    Allora sull'exchange la posizione long di "alfa" su "BTC" ha lo stop loss a 97000 e il take profit a 110000
