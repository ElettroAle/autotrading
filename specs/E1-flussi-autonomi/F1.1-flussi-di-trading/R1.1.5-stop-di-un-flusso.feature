# language: it
@R1.1.5 @wip
Funzionalità: R1.1.5 Stop di un flusso
  Come utente
  Voglio fermare un flusso chiudendone le posizioni
  Perché nessuna posizione resti sull'exchange senza un flusso che la gestisca

  Lo stop vale per un flusso attivo o in pausa. Il flusso smette di eseguire cicli e tutte le sue posizioni
  aperte vengono chiuse subito: finché sull'exchange non ci sono stop loss e take profit, una posizione lasciata
  aperta non è protetta da nulla. Se lo stop arriva durante un ciclo, il ciclo in corso si conclude prima della
  chiusura delle posizioni.
  Se la chiusura di una posizione fallisce, il flusso è comunque fermo e l'esito dello stop riporta la posizione
  rimasta aperta con il motivo dell'exchange.
  Un flusso fermo si può avviare di nuovo.

  Fuori ambito: la scelta di lasciare aperte le posizioni allo stop, che arriva con le protezioni sull'exchange.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con posizioni aperte su "BTC" e "ETH"

  Scenario: Stop con chiusura delle posizioni
    Quando "anna" ferma il flusso "alfa"
    Allora il flusso "alfa" è nello stato "fermo"
    E sull'exchange il flusso "alfa" non ha posizioni aperte
    E il flusso "alfa" non esegue cicli

  Scenario: Stop di un flusso in pausa
    Dato che il flusso "alfa" è in pausa
    Quando "anna" ferma il flusso "alfa"
    Allora il flusso "alfa" è nello stato "fermo"
    E sull'exchange il flusso "alfa" non ha posizioni aperte

  Scenario: Stop durante un ciclo
    Dato che un ciclo del flusso "alfa" è in corso
    Quando "anna" ferma il flusso "alfa"
    Allora il ciclo in corso si conclude
    E dopo il ciclo le posizioni del flusso "alfa" vengono chiuse

  Scenario: Chiusura fallita di una posizione
    Dato che l'exchange rifiuta la chiusura della posizione su "ETH" con il messaggio "Order rejected"
    Quando "anna" ferma il flusso "alfa"
    Allora il flusso "alfa" è nello stato "fermo"
    E l'esito dello stop riporta la posizione su "ETH" rimasta aperta con il motivo "Order rejected"
    E sull'exchange la posizione su "BTC" è chiusa

  Scenario: Riavvio di un flusso fermo
    Dato che il flusso "alfa" è fermo
    Quando "anna" avvia il flusso "alfa"
    Allora il flusso "alfa" è nello stato "attivo"
