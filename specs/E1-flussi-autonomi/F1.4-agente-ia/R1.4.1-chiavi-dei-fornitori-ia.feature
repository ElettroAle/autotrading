# language: it
@R1.4.1
Funzionalità: R1.4.1 Chiavi dei fornitori IA dell'utente
  Come utente
  Voglio registrare le mie chiavi dei fornitori di modelli IA
  Perché i miei flussi usino i modelli a mie spese, con il mio account presso il fornitore

  L'utente registra al massimo una chiave per fornitore; può sostituirla e rimuoverla.
  Alla registrazione e alla sostituzione la piattaforma verifica la chiave presso il fornitore; una chiave
  rifiutata non si registra. La chiave è conservata come le credenziali dei conti: non compare mai in una
  risposta, in un log o nel contesto inviato all'agente, e la usa solo il servizio che esegue i cicli.
  Un flusso può usare solo modelli di fornitori di cui l'utente ha registrato la chiave.
  La rimozione della chiave di un fornitore usato da flussi attivi o in pausa è rifiutata.

  Fuori ambito: chiavi condivise tra utenti, limiti di spesa impostati sulla piattaforma.

  Contesto:
    Dato che "anna" non ha chiavi di fornitori IA registrate

  Scenario: Registrazione di una chiave valida
    Dato che il fornitore "openrouter" accetta la chiave "K-OR"
    Quando "anna" registra la chiave "K-OR" per il fornitore "openrouter"
    Allora "anna" ha una chiave registrata per il fornitore "openrouter"
    E la chiave "K-OR" non compare nella risposta

  Scenario: Chiave rifiutata dal fornitore
    Dato che il fornitore "openrouter" rifiuta la chiave "K-BAD"
    Quando "anna" registra la chiave "K-BAD" per il fornitore "openrouter"
    Allora la registrazione è rifiutata con il motivo "chiave rifiutata dal fornitore: openrouter"
    E "anna" non ha chiavi registrate per il fornitore "openrouter"

  @wip
  Scenario: Sostituzione della chiave
    Dato che "anna" ha registrato la chiave "K-OR" per il fornitore "openrouter"
    E che il fornitore "openrouter" accetta la chiave "K-OR2"
    Quando "anna" sostituisce la chiave del fornitore "openrouter" con "K-OR2"
    Allora i cicli successivi dei flussi di "anna" usano la chiave "K-OR2" presso "openrouter"

  @wip
  Scenario: Flusso con modello di un fornitore senza chiave
    Quando "anna" crea il flusso "alfa" con modello "anthropic/claude-sonnet"
    Allora la creazione è rifiutata con il motivo "nessuna chiave registrata per il fornitore: anthropic"

  @wip
  Scenario: Rimozione rifiutata se un flusso non fermo usa la chiave
    Dato che "anna" ha registrato la chiave "K-OR" per il fornitore "openrouter"
    E che "anna" ha il flusso "alfa" attivo con modello "openrouter/deepseek-chat"
    Quando "anna" rimuove la chiave del fornitore "openrouter"
    Allora la rimozione è rifiutata con il motivo "chiave usata da flussi attivi o in pausa: alfa"

  @wip
  Scenario: La chiave non è mai esposta
    Dato che "anna" ha registrato la chiave "K-OR" per il fornitore "openrouter"
    Quando il flusso "alfa" di "anna" esegue un ciclo
    Allora la chiave "K-OR" non compare nel contesto inviato all'agente
    E la chiave "K-OR" non compare nei log
    E la chiave "K-OR" non compare nel ciclo registrato
