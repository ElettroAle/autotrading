# language: it
@R1.4.1
Funzionalità: R1.4.1 Chiavi dei fornitori IA dell'utente
  Come utente
  Voglio registrare le mie chiavi dei fornitori di modelli IA
  Perché i miei flussi usino i modelli a mie spese, con il mio account presso il fornitore

  L'utente registra al massimo una chiave per fornitore; può sostituirla e rimuoverla.
  La piattaforma non verifica la chiave presso il fornitore alla registrazione né alla sostituzione: una chiave
  non valida si scopre al primo ciclo, come errore permanente che mette in pausa i flussi che la usano (R1.2.4).
  La chiave è conservata come le credenziali dei conti: non compare mai in una
  risposta, in un log o nel contesto inviato all'agente, e la usa solo il servizio che esegue i cicli.
  Un flusso può usare solo modelli di fornitori di cui l'utente ha registrato la chiave.
  La rimozione della chiave di un fornitore usato da flussi attivi o in pausa è rifiutata.

  Fuori ambito: chiavi condivise tra utenti, limiti di spesa impostati sulla piattaforma.

  Contesto:
    Dato che "anna" non ha chiavi di fornitori IA registrate

  Scenario: La chiave non è mai esposta
    Dato che "anna" ha registrato la chiave "K-OR" per il fornitore "openrouter"
    Quando il flusso "alfa" di "anna" esegue un ciclo
    Allora la chiave "K-OR" non compare nel contesto inviato all'agente
    E la chiave "K-OR" non compare nei log
    E la chiave "K-OR" non compare nel ciclo registrato
