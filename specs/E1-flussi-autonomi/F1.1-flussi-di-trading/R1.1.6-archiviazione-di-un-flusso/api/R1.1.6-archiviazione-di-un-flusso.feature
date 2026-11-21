# language: it
@R1.1.6
Funzionalità: R1.1.6 Archiviazione di un flusso
  Come utente
  Voglio archiviare un flusso che non uso più
  Perché non compaia tra i flussi in uso ma il suo storico resti consultabile

  Si archivia solo un flusso fermo. L'archiviazione è definitiva: un flusso archiviato non si avvia e non si
  modifica. Il suo capitale allocato torna capitale libero del conto e i suoi asset tornano disponibili per gli
  altri flussi del conto. Cicli, versioni della configurazione e posizioni chiuse restano consultabili.

  Fuori ambito: la cancellazione dei dati di un flusso.

  Contesto:
    Dato che "anna" ha il conto "test-1" con saldo 1000 USDC
    E che "anna" ha il flusso "alfa" sul conto "test-1" con capitale allocato 400 USDC e 12 cicli registrati

  Scenario: Archiviazione di un flusso fermo
    Dato che il flusso "alfa" è fermo
    Quando "anna" archivia il flusso "alfa"
    Allora il flusso "alfa" non compare tra i flussi in uso di "anna"
    E il flusso "alfa" compare tra i flussi archiviati di "anna"
    E il capitale libero del conto "test-1" è 1000 USDC
    E i 12 cicli del flusso "alfa" restano consultabili

  Schema dello scenario: Archiviazione rifiutata per un flusso non fermo
    Dato che il flusso "alfa" è nello stato "<stato>"
    Quando "anna" archivia il flusso "alfa"
    Allora l'archiviazione è rifiutata con il motivo "si archivia solo un flusso fermo"

    Esempi:
      | stato    |
      | attivo   |
      | in pausa |

  Scenario: Un flusso archiviato non si modifica
    Dato che il flusso "alfa" è archiviato
    Quando "anna" modifica il modello del flusso "alfa"
    Allora la modifica è rifiutata con il motivo "un flusso archiviato non si modifica"

  Scenario: Un flusso archiviato non si avvia
    Dato che il flusso "alfa" è archiviato
    Quando "anna" avvia il flusso "alfa"
    Allora l'avvio è rifiutato con il motivo "comando avvia non ammesso per un flusso archiviato"
    E il flusso "alfa" è nello stato "archiviato"

  Scenario: Versioni e posizioni chiuse di un flusso archiviato restano consultabili
    Dato che il flusso "alfa" ha 2 versioni della configurazione e una posizione chiusa su "BTC"
    E che il flusso "alfa" è archiviato
    Allora le 2 versioni della configurazione del flusso "alfa" restano consultabili
    E la posizione chiusa su "BTC" del flusso "alfa" resta consultabile
