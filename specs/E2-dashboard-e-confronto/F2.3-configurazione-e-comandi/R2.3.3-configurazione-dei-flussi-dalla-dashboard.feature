# language: it
@R2.3.3
Funzionalità: R2.3.3 Creazione e modifica dei flussi dalla dashboard
  Come utente
  Voglio creare e modificare un flusso dalla dashboard
  Perché configuri le strategie senza scrivere richieste a mano

  Dalla dashboard l'utente crea un flusso e ne modifica la configurazione: nome, conto, asset, intervallo,
  fonti attive con pesi e parametri, modello con temperatura, limite di token e livello di ragionamento,
  istruzioni, regole di rischio, capitale allocato (RF-23.11), con le regole e i messaggi di errore
  dell'interfaccia programmatica (R1.1.1, R1.1.2, R1.1.3, R1.1.7, R1.3.2, R1.4.2). Le scelte di fonti e
  modelli vengono dai cataloghi (R1.3.1, R1.4.2). Ogni modifica crea una nuova versione e vale dal ciclo
  successivo. Ogni errore si mostra accanto al campo che lo causa.

  Fuori ambito: incasso e riduzione del capitale (F3), exit plan e regole di rischio avanzate (F3).

  Contesto:
    Dato che "anna" ha il conto "principale" con capitale libero 500 USDC e una chiave per "openrouter"

  Scenario: Creazione di un flusso
    Quando "anna" crea il flusso "alfa" su "principale" con asset "BTC", intervallo 15 minuti, fonti "indicatori" peso 2 e "sentiment" peso 1, modello "openrouter/deepseek-chat" e capitale 300 USDC
    Allora il flusso "alfa" compare nell'elenco nello stato "fermo" alla versione 1

  Scenario: Configurazione rifiutata
    Quando "anna" crea un flusso con capitale 600 USDC su "principale"
    Allora la dashboard mostra il motivo del rifiuto accanto al capitale
    E il flusso non viene creato

  Scenario: Modifica della configurazione
    Dato che il flusso "alfa" è alla versione 1
    Quando "anna" cambia il peso della fonte "sentiment" a 3
    Allora il flusso "alfa" è alla versione 2 con peso 3 per "sentiment"

  Scenario: Asset già in uso sullo stesso conto
    Dato che il flusso "beta" usa "ETH" sul conto "principale"
    Quando "anna" aggiunge "ETH" al flusso "alfa"
    Allora la dashboard mostra che "ETH" è già usato dal flusso "beta"
