# language: it
@R5.5.3
Funzionalità: R5.5.3 Stop in vigore sempre visibile
  Come utente, e come agente
  Voglio vedere sempre il prezzo dello stop loss e del take profit che proteggono davvero la posizione
  Perché lo stato di una posizione non dica «stop: nessuno» mentre sull'exchange c'è uno stop

  Ogni posizione ha sull'exchange un ordine di stop loss (R3.1.2). Quando lo stop viene dal predefinito del flusso, lo
  stato della posizione lo mostrava vuoto: all'agente, in API, negli strumenti MCP e nella dashboard. Visto il 25
  novembre 2026 su flussi con stop predefinito 40%: l'agente e l'utente leggevano «stop: nessuno». Lo stesso vale per
  il take profit predefinito.

  Lo stato di una posizione aperta riporta il livello di stop loss e di take profit che la piattaforma ha inviato
  all'exchange per quella posizione, qualunque sia la sua origine: predefinito del flusso, livello dell'agente, stop
  riportato entro il predefinito.

  Fonte del livello: la piattaforma registra il livello ogni volta che mette o sostituisce un ordine di protezione, e
  lo stato legge quel livello registrato. Per una posizione aperta prima di questo requisito, senza livello
  registrato, la piattaforma lo legge una volta dagli ordini di protezione presenti sull'exchange e lo registra.

  Vale allo stesso modo per lo stato inviato all'agente, per l'API, per gli strumenti MCP e per la dashboard. Una
  posizione senza ordine di take profit riporta l'obiettivo vuoto. Decisione del proprietario: l'agente lo riceve
  sempre, senza opzione.

  Fuori ambito: cambiare come lo stop viene calcolato o riportato entro il predefinito.

  Scenario: Stop predefinito dagli strumenti
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC" e stop loss predefinito 5%
    E che "alfa" ha aperto long su "BTC" al prezzo d'ingresso 60000 senza piano di uscita
    Quando il client MCP di "anna" legge lo stato di "alfa"
    Allora la posizione su "BTC" riporta stop 57000
