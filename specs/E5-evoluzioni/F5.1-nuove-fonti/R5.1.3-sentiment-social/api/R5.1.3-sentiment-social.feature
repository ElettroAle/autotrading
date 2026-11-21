# language: it
@R5.1.3
Funzionalità: R5.1.3 Sentiment social
  Come utente
  Voglio che l'agente sappia cosa si dice di un asset sui social
  Perché i messaggi di persone influenti muovono il mercato

  Nuova fonte per asset "social" con un adapter, LunarCrush (chiave a pagamento, da configurare in Impostazioni ›
  Chiavi, R4.1.2): non esiste un fornitore gratuito di dati social. Per ogni asset del flusso: sentiment social,
  volume di menzioni e interazioni nelle ultime 24 ore, e i messaggi più rilevanti dei creatori più influenti,
  con autore, data e testo (RF-10.03). Il numero di messaggi è un parametro dell'adapter (predefinito 5).

  Fuori ambito: X e altri fornitori social, aggiungibili come adapter.

  Contesto:
    Dato che il flusso "alfa" ha l'asset "BTC" e la fonte "social" con l'adapter "LunarCrush" configurato

  Scenario: Adapter non configurato
    Dato che "anna" non ha configurato l'adapter "LunarCrush"
    Quando "anna" prova ad attivare la fonte "social" nel flusso "alfa"
    Allora l'attivazione è rifiutata con il motivo "configura l'adapter LunarCrush in Impostazioni › Chiavi"
