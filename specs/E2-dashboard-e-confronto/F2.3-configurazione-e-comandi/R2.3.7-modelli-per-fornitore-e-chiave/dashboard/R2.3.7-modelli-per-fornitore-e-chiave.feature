# language: it
@R2.3.7
Funzionalità: R2.3.7 Modelli per fornitore e chiave nel modulo del flusso
  Come utente
  Voglio vedere, scegliendo il modello di un flusso, di quale fornitore è e se ne ho registrato la chiave
  Perché sappia quale chiave serve (OpenRouter o il fornitore diretto) prima di salvare il flusso

  La tendina del modello raggruppa i modelli del catalogo (R1.4.2) per fornitore; ogni gruppo nomina il
  fornitore e se la sua chiave è registrata. Un modello del cui fornitore manca la chiave resta visibile ma
  non si può scegliere, e il modulo offre il collegamento alla pagina delle chiavi IA (R2.3.2). Il fornitore
  di un modello, e quindi la chiave che usa, è quello del suo nome: "openrouter/..." usa la chiave OpenRouter.

  Fuori ambito: la scelta esplicita dell'instradamento separata dal modello.

  Contesto:
    Dato che il catalogo contiene i modelli "openrouter/deepseek-chat" e "anthropic/claude-sonnet"
    E che "anna" ha registrato la chiave del fornitore "openrouter"
    E che "anna" non ha registrato la chiave del fornitore "anthropic"

  Scenario: Modelli raggruppati per fornitore con lo stato della chiave
    Quando "anna" apre il modulo di creazione di un flusso
    Allora la tendina del modello ha il gruppo "openrouter" con chiave registrata che contiene "openrouter/deepseek-chat"
    E ha il gruppo "anthropic" con chiave mancante che contiene "anthropic/claude-sonnet"

  Scenario: Modello senza chiave non selezionabile
    Quando "anna" apre il modulo di creazione di un flusso
    Allora il modello "anthropic/claude-sonnet" non si può scegliere
    E il modulo offre il collegamento alle chiavi IA

  Scenario: Modello con chiave selezionabile
    Quando "anna" sceglie il modello "openrouter/deepseek-chat" nel modulo di creazione di un flusso
    Allora il modulo mostra i parametri del modello "openrouter/deepseek-chat"

  Scenario: Flusso esistente su un modello la cui chiave è stata rimossa
    Dato che "anna" ha il flusso "alfa" con modello "anthropic/claude-sonnet"
    Quando "anna" apre la modifica del flusso "alfa"
    Allora il modello "anthropic/claude-sonnet" resta indicato come scelta attuale con chiave mancante
