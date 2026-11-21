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

  Scenario: La configurazione mostra il system prompt predefinito e i segnaposti
    Quando "anna" consulta la configurazione del flusso "alfa"
    Allora il system prompt è il testo predefinito, indicato come predefinito
    E la configurazione elenca i segnaposti "instructions, actions, max_leverage, assets, source_weights" ciascuno con la sua descrizione

  Scenario: Segnaposto sconosciuto
    Quando "anna" imposta il system prompt "Leva al massimo {leverage}"
    Allora la modifica è rifiutata perché il segnaposto "leverage" non esiste

  Scenario: Ritorno al predefinito
    Dato che "anna" ha impostato un system prompt personalizzato
    Quando "anna" ripristina il system prompt predefinito
    Allora la configurazione del flusso "alfa" mostra il testo predefinito, indicato come predefinito
