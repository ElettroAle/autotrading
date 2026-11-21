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
  Un limite di esposizione svuotato si toglie dalla nuova versione, purché resti almeno l'altro; un limite non
  modificato resta quello in vigore.
  Il conto di un flusso non si cambia: per operare su un altro conto si crea un altro flusso.
  Il capitale allocato si modifica con R1.1.7.

  Fuori ambito: la duplicazione di un flusso, l'esportazione e l'importazione della configurazione.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC, ETH" e modello "openrouter/deepseek-chat" alla versione 1

  Scenario: La modifica non tocca il ciclo in corso
    Dato che un ciclo del flusso "alfa" è in corso con la versione 1
    Quando "anna" modifica il modello del flusso "alfa" in "anthropic/claude-sonnet"
    Allora il ciclo in corso si conclude con la versione 1
    E il ciclo successivo del flusso "alfa" usa la versione 2
