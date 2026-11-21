# language: it
@R1.4.8
Funzionalità: R1.4.8 System prompt del flusso personalizzabile
  Come utente
  Voglio vedere nella configurazione del flusso il system prompt che l'agente riceve, col testo predefinito, e
  poterlo modificare
  Perché la strategia del flusso possa cambiare tutte le indicazioni che la piattaforma dà all'agente

  Il system prompt è un modello di testo con segnaposti in inglese che il ciclo sostituisce coi valori del flusso:
  {instructions} (le istruzioni del flusso), {actions} (azioni ammesse), {max_leverage} (leva massima), {assets}
  (asset del flusso), {source_weights} (la regola del peso delle fonti e i pesi delle fonti attive, R1.3.2). Il
  pannello della configurazione elenca sotto il testo i segnaposti con la loro descrizione.
  Il predefinito comprende istruzioni, regole operative (R1.4.3, R1.4.7), regola del peso delle fonti (R1.3.2) e
  formato della risposta. Un segnaposto sconosciuto è rifiutato. L'utente può tornare al predefinito; finché non lo cambia, il flusso segue il predefinito
  anche se la piattaforma lo aggiorna. La modifica è una nuova versione della configurazione (R1.1.3).
  Restano fissi il messaggio coi dati del ciclo, lo schema della risposta passato al modello (Bug 416) e i controlli
  del codice: il testo cambia ciò che il modello legge, non ciò che validazione e controllo del rischio accettano.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC", leva massima 3 e istruzioni "Sei un trader prudente"

  Scenario: System prompt personalizzato con i valori del flusso
    Dato che "anna" imposta il system prompt "{instructions}. Leva al massimo {max_leverage} su {assets}, mai contro trend"
    Quando il flusso "alfa" esegue un ciclo
    Allora il system prompt inviato all'agente è "Sei un trader prudente. Leva al massimo 3 su BTC, mai contro trend"

  Scenario: Lo schema della risposta resta vincolante
    Dato che "anna" imposta il system prompt "{instructions}" senza il formato della risposta
    Quando il flusso "alfa" esegue un ciclo
    Allora la chiamata al modello chiede comunque la risposta nel formato delle decisioni

  Scenario: Il flusso segue il predefinito aggiornato dalla piattaforma
    Dato che il flusso "alfa" segue il system prompt predefinito
    E che la piattaforma aggiorna il system prompt predefinito in "{instructions}. Testo aggiornato su {assets}"
    Quando il flusso "alfa" esegue un ciclo
    Allora il system prompt inviato all'agente è "Sei un trader prudente. Testo aggiornato su BTC"
    E il flusso "alfa" resta alla versione di configurazione 1
