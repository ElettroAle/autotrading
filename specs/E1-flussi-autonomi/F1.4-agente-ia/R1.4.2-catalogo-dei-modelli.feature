# language: it
@R1.4.2 @wip
Funzionalità: R1.4.2 Catalogo dei modelli IA
  Come utente
  Voglio consultare i fornitori e i modelli IA disponibili con i parametri ammessi
  Perché sappia quale modello posso scegliere per un flusso e come regolarlo

  Il catalogo elenca per ogni modello: fornitore, nome, parametri ammessi con valore predefinito e valori
  ammessi (per esempio temperatura, limite di lunghezza della risposta, livello di ragionamento se il modello lo
  supporta). Per ogni fornitore indica se l'utente ne ha registrato la chiave.
  Un modello aggiunto alla piattaforma compare nel catalogo e diventa selezionabile nei flussi con la sola
  configurazione. Un parametro non ammesso dal modello rende la configurazione del flusso non valida.

  Fuori ambito: il costo stimato per ciclo di un modello.

  Contesto:
    Dato che il catalogo contiene il modello "openrouter/deepseek-chat" con temperatura da 0 a 2, predefinita 1
    E che "anna" ha registrato la chiave del fornitore "openrouter"

  Scenario: Consultazione del catalogo
    Quando "anna" consulta il catalogo dei modelli
    Allora il catalogo contiene il modello "openrouter/deepseek-chat" con il parametro temperatura da 0 a 2, predefinita 1
    E il fornitore "openrouter" risulta con chiave registrata

  Scenario: Parametro fuori dai valori ammessi
    Quando "anna" crea il flusso "alfa" con modello "openrouter/deepseek-chat" e temperatura 3
    Allora la creazione è rifiutata con il motivo "parametro fuori dai valori ammessi: temperatura"

  Scenario: Parametro non supportato dal modello
    Dato che il modello "openrouter/deepseek-chat" non supporta il livello di ragionamento
    Quando "anna" crea il flusso "alfa" con modello "openrouter/deepseek-chat" e livello di ragionamento "alto"
    Allora la creazione è rifiutata con il motivo "parametro non supportato dal modello: livello di ragionamento"

  Scenario: Parametri predefiniti
    Quando "anna" crea il flusso "alfa" con modello "openrouter/deepseek-chat" senza parametri
    Allora il flusso "alfa" usa la temperatura 1
