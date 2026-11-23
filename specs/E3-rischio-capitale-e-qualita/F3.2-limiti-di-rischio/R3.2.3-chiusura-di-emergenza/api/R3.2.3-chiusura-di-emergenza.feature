# language: it
@R3.2.3
Funzionalità: R3.2.3 Chiusura di emergenza
  Come utente
  Voglio chiudere con un solo comando tutte le posizioni di un flusso, di un conto o di tutti i miei flussi
  Perché in una situazione critica esco subito dal mercato senza agire flusso per flusso

  Il comando si lancia dall'interfaccia programmatica e dalla dashboard, con uno di tre ambiti: un flusso, un
  conto (tutti i suoi flussi), tutti i flussi dell'utente (RF-18.09, RF-21.07, RF-23.13).
  Per ogni flusso dell'ambito la piattaforma chiude a mercato tutte le posizioni, annulla gli ordini di protezione
  (R3.1.2) e mette il flusso in pausa con il motivo "chiusura di emergenza". Un flusso già in pausa resta in pausa e
  le sue posizioni si chiudono. I flussi fermi o archiviati non hanno posizioni e non vengono toccati.
  Le posizioni che nessun flusso possiede non vengono toccate (R1.6.2).
  Una chiusura che fallisce non ferma le altre: l'esito elenca, per flusso, le posizioni chiuse e quelle non chiuse
  con il motivo. Il flusso va in pausa anche se una sua chiusura è fallita.
  Ogni chiusura entra nello storico delle posizioni chiuse con il motivo "chiusura di emergenza". Il comando si
  registra con data, ora, ambito ed esito.
  Le esecuzioni delle chiusure appartengono al flusso chiuso, anche se il suo asset passa a un altro flusso prima che
  il registro delle operazioni le legga (Bug 684).
  La dashboard chiede una conferma che nomina l'ambito e il numero di posizioni da chiudere.
  Nella dashboard il comando sta da solo nel riquadro "Zona di emergenza", in fondo alla pagina del conto e della
  pagina "Generale" delle impostazioni, lontano dagli altri comandi (Bug 545, Bug 632); l'elenco dei flussi e quello
  dei conti, le pagine d'uso quotidiano, non lo offrono (Bug 563, Bug 632). La chiusura di emergenza di un flusso sta
  nel riquadro "Zona pericolosa" in fondo alla pagina Impostazioni del flusso, con Archivia, e non nella pagina del
  flusso (Bug 560).
  I flussi riprendono solo per comando dell'utente (R1.1.4).
  Fuori ambito: la procedura di verifica dell'esecuzione, già disponibile (R0.4.1).

  Contesto:
    Dato che "anna" ha sul conto "test-1" i flussi attivi "alfa" con una posizione su "BTC" e "beta" con una posizione su "ETH"
    E che "anna" ha sul conto "test-2" il flusso attivo "gamma" con una posizione su "SOL"

  Scenario: Chiusura di emergenza di un flusso
    Quando "anna" lancia la chiusura di emergenza del flusso "alfa"
    Allora la posizione di "alfa" su "BTC" è chiusa
    E il flusso "alfa" è in pausa con motivo "chiusura di emergenza"
    E i flussi "beta" e "gamma" restano attivi con le loro posizioni

  Scenario: Chiusura di emergenza di un conto
    Quando "anna" lancia la chiusura di emergenza del conto "test-1"
    Allora le posizioni di "alfa" e "beta" sono chiuse
    E i flussi "alfa" e "beta" sono in pausa con motivo "chiusura di emergenza"
    E il flusso "gamma" resta attivo con la sua posizione

  Scenario: Chiusura di emergenza di tutti i flussi
    Quando "anna" lancia la chiusura di emergenza di tutti i suoi flussi
    Allora le posizioni di "alfa", "beta" e "gamma" sono chiuse
    E i flussi "alfa", "beta" e "gamma" sono in pausa con motivo "chiusura di emergenza"

  Scenario: Gli ordini di protezione si annullano
    Dato che la posizione di "alfa" su "BTC" ha un ordine di stop loss sull'exchange
    Quando "anna" lancia la chiusura di emergenza del flusso "alfa"
    Allora sull'exchange non resta alcun ordine di protezione di "alfa" su "BTC"

  Scenario: Motivo nello storico
    Quando "anna" lancia la chiusura di emergenza del flusso "alfa"
    Allora lo storico delle posizioni chiuse di "alfa" contiene "BTC" con motivo "chiusura di emergenza"

  Scenario: Posizione di nessun flusso
    Dato che sul conto "test-1" c'è una posizione su "DOGE" che nessun flusso possiede
    Quando "anna" lancia la chiusura di emergenza del conto "test-1"
    Allora la posizione su "DOGE" resta aperta

  Scenario: Una chiusura fallita non ferma le altre
    Dato che l'exchange rifiuta la chiusura su "BTC" con "Order rejected"
    Quando "anna" lancia la chiusura di emergenza del conto "test-1"
    Allora la posizione di "beta" su "ETH" è chiusa
    E l'esito riporta per "alfa" la posizione "BTC" non chiusa con "Order rejected"
    E il flusso "alfa" è in pausa con motivo "chiusura di emergenza"

  Scenario: Flusso già in pausa
    Dato che il flusso "alfa" è in pausa con la posizione su "BTC" aperta
    Quando "anna" lancia la chiusura di emergenza del flusso "alfa"
    Allora la posizione di "alfa" su "BTC" è chiusa
    E il flusso "alfa" resta in pausa

  Scenario: Nessuna posizione da chiudere
    Dato che "anna" ha sul conto "test-2" anche il flusso attivo "delta" senza posizioni
    Quando "anna" lancia la chiusura di emergenza del flusso "delta"
    Allora l'esito riporta "nessuna posizione da chiudere"
    E il flusso "delta" è in pausa con motivo "chiusura di emergenza"

  Scenario: Conferma nella dashboard
    Quando "anna" sceglie nella dashboard la chiusura di emergenza del conto "test-1"
    Allora la dashboard chiede conferma con "Chiudere 2 posizioni dei flussi del conto test-1 e metterli in pausa?"
    E nessuna posizione viene chiusa finché "anna" non conferma

  Scenario: Flusso di un altro tenant
    Dato che "bruno" ha il flusso "omega" con una posizione aperta
    Quando "anna" lancia la chiusura di emergenza del flusso "omega"
    Allora il comando viene rifiutato come flusso inesistente
    E la posizione di "omega" resta aperta

  Scenario: Zona pericolosa in fondo alle impostazioni del flusso
    Quando "anna" apre nella dashboard le impostazioni del flusso "alfa"
    Allora la chiusura di emergenza del flusso "alfa" sta nel riquadro "Zona pericolosa" in fondo alla pagina
    E la pagina del flusso "alfa" non contiene la chiusura di emergenza

  Scenario: Zona di emergenza in fondo alla pagina del conto
    Quando "anna" apre nella dashboard la pagina del conto "test-1"
    Allora la chiusura di emergenza del conto "test-1" sta nel riquadro "Zona di emergenza" in fondo alla pagina
    E l'elenco dei conti non contiene la chiusura di emergenza

  Scenario: Zona di emergenza nelle impostazioni generali
    Quando "anna" apre nella dashboard le impostazioni generali
    Allora la chiusura di emergenza di tutti i flussi sta nel riquadro "Zona di emergenza" in fondo alla pagina
    E il riquadro "Zona di emergenza" non contiene altri comandi
    E l'elenco dei flussi non contiene la chiusura di emergenza

  Scenario: Conferma dalla zona pericolosa
    Quando "anna" sceglie la chiusura di emergenza del flusso "alfa" nel riquadro "Zona pericolosa"
    Allora la dashboard chiede conferma con "Chiudere 1 posizione del flusso alfa e metterlo in pausa?"
    E nessuna posizione viene chiusa finché "anna" non conferma

  Schema dello scenario: Flussi fermi o archiviati non toccati
    Dato che "anna" ha sul conto "test-1" anche il flusso <stato> "epsilon"
    Quando "anna" lancia la chiusura di emergenza del conto "test-1"
    Allora il flusso "epsilon" resta <stato>
    E l'esito non riporta il flusso "epsilon"

    Esempi:
      | stato      |
      | fermo      |
      | archiviato |

  Scenario: Il comando si registra con data, ora, ambito ed esito
    Dato che sono le 10:30 UTC del 12 novembre 2026
    Quando "anna" lancia la chiusura di emergenza del conto "test-1"
    Allora la chiusura di emergenza è registrata alle 10:30 UTC del 12 novembre 2026 con ambito il conto "test-1"
    E la chiusura registrata riporta chiuse le posizioni di "alfa" su "BTC" e di "beta" su "ETH"

  Scenario: La chiusura di emergenza attribuisce la chiusura al flusso chiuso anche se l'asset passa a un altro flusso
    Dato che il registro del flusso "alfa" riporta le sue posizioni aperte
    Quando "anna" lancia la chiusura di emergenza del flusso "alfa"
    E "anna" ferma e archivia il flusso "alfa" e aggiunge "BTC" agli asset del flusso "beta"
    E il flusso "beta" esegue un ciclo che registra le esecuzioni delle chiusure
    Allora il registro del flusso "alfa" riporta la chiusura su "BTC" e nessuna posizione aperta
    E il registro del flusso "beta" non ha una posizione su "BTC"
    E il flusso "beta" non è in pausa
