# language: it
@R1.1.3
Funzionalità: R1.1.3 Modifica versionata della configurazione
  Come utente
  Voglio modificare la configurazione di un flusso conservando le versioni precedenti
  Perché ogni ciclo sia ricostruibile con la configurazione che era in vigore e possa confrontare le versioni

  Ogni modifica accettata crea una nuova versione, numerata in ordine crescente; le versioni precedenti restano
  consultabili. Una modifica ha effetto dal ciclo successivo, mai su un ciclo in corso.
  Una modifica non valida è rifiutata con il motivo e la versione in vigore resta invariata: valgono le stesse
  regole di validità della creazione (R1.1.1) e la regola di conflitto (R1.1.2).
  Non si può togliere dal flusso un asset su cui il flusso ha una posizione aperta.
  Il conto di un flusso non si cambia: per operare su un altro conto si crea un altro flusso.
  Il capitale allocato si modifica con R1.1.7.

  Fuori ambito: la duplicazione di un flusso, l'esportazione e l'importazione della configurazione.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC, ETH" e modello "openrouter/deepseek-chat" alla versione 1

  Scenario: Una modifica crea una nuova versione
    Quando "anna" modifica il modello del flusso "alfa" in "anthropic/claude-sonnet"
    Allora il flusso "alfa" ha la versione di configurazione 2 con modello "anthropic/claude-sonnet"
    E la versione 1 del flusso "alfa" resta consultabile con modello "openrouter/deepseek-chat"

  Scenario: Confronto tra due versioni
    Dato che il flusso "alfa" ha la versione 2 con modello "anthropic/claude-sonnet"
    Quando "anna" confronta le versioni 1 e 2 del flusso "alfa"
    Allora il confronto riporta solo la differenza sul modello, da "openrouter/deepseek-chat" a "anthropic/claude-sonnet"

  @wip
  Scenario: La modifica non tocca il ciclo in corso
    Dato che un ciclo del flusso "alfa" è in corso con la versione 1
    Quando "anna" modifica il modello del flusso "alfa" in "anthropic/claude-sonnet"
    Allora il ciclo in corso si conclude con la versione 1
    E il ciclo successivo del flusso "alfa" usa la versione 2

  Scenario: Modifica non valida rifiutata
    Quando "anna" modifica l'intervallo di ciclo del flusso "alfa" in 0 minuti
    Allora la modifica è rifiutata con il motivo "intervallo di ciclo fuori da 1-1440 minuti"
    E il flusso "alfa" resta alla versione di configurazione 1

  @wip
  Scenario: Non si toglie un asset con posizione aperta
    Dato che il flusso "alfa" ha una posizione aperta su "ETH"
    Quando "anna" modifica gli asset del flusso "alfa" in "BTC"
    Allora la modifica è rifiutata con il motivo "posizione aperta sull'asset da togliere: ETH"
    E il flusso "alfa" resta alla versione di configurazione 1

  Scenario: Il conto non si cambia
    Quando "anna" modifica il conto del flusso "alfa"
    Allora la modifica è rifiutata con il motivo "il conto di un flusso non si cambia"
