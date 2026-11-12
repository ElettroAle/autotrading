# language: it
@R1.1.2
Funzionalità: R1.1.2 Regola di conflitto sugli asset del conto
  Come utente
  Voglio che due flussi dello stesso conto non operino mai lo stesso asset
  Perché ogni posizione sull'exchange sia attribuibile a un solo flusso senza ambiguità

  La regola vale sia alla creazione sia alla modifica della configurazione di un flusso.
  Un flusso archiviato non partecipa alla regola. Flussi di conti diversi possono avere asset in comune.

  Fuori ambito: il netting tra flussi dello stesso conto (BL-03).

  Contesto:
    Dato che "anna" ha i conti "test-1" e "test-2"
    E che "anna" ha il flusso "alfa" sul conto "test-1" con asset "BTC, ETH"

  Scenario: Creazione rifiutata per asset in comune sullo stesso conto
    Quando "anna" crea il flusso "beta" sul conto "test-1" con asset "ETH, SOL"
    Allora la creazione è rifiutata con il motivo "asset già assegnati al flusso alfa sullo stesso conto: ETH"

  Scenario: Modifica rifiutata per asset in comune sullo stesso conto
    Dato che "anna" ha il flusso "beta" sul conto "test-1" con asset "SOL"
    Quando "anna" modifica gli asset del flusso "beta" in "SOL, BTC"
    Allora la modifica è rifiutata con il motivo "asset già assegnati al flusso alfa sullo stesso conto: BTC"
    E il flusso "beta" ha ancora gli asset "SOL"

  Scenario: Asset disgiunti sullo stesso conto
    Quando "anna" crea il flusso "beta" sul conto "test-1" con asset "SOL"
    Allora "anna" ha il flusso "beta"

  Scenario: Stesso asset su conti diversi
    Quando "anna" crea il flusso "beta" sul conto "test-2" con asset "BTC"
    Allora "anna" ha il flusso "beta"

  Scenario: Un flusso archiviato libera i suoi asset
    Dato che il flusso "alfa" è archiviato
    Quando "anna" crea il flusso "beta" sul conto "test-1" con asset "BTC"
    Allora "anna" ha il flusso "beta"
