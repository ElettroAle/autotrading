# language: it
@R1.1.8 @wip
Funzionalità: R1.1.8 Rimozione di un conto con flussi assegnati
  Come utente
  Voglio che la rimozione di un conto fermi prima i flussi che vi operano
  Perché nessun flusso continui a operare su un conto che non esiste più

  Completa la rimozione di un conto (R0.2.5) con il vincolo sui flussi, rinviato a quando i flussi esistono.
  La rimozione di un conto con flussi attivi o in pausa chiede conferma. Con la conferma, ogni flusso attivo o in
  pausa del conto viene fermato come in R1.1.5, chiudendone le posizioni, e poi il conto viene rimosso.
  I flussi del conto, fermi e ora senza conto, vengono archiviati; il loro storico resta consultabile.
  Se la chiusura di una posizione fallisce, il conto non viene rimosso e l'esito riporta la posizione rimasta
  aperta con il motivo dell'exchange; i flussi restano fermi.

  Fuori ambito: le posizioni aperte sul conto non attribuite ad alcun flusso, che seguono R0.2.5.

  Contesto:
    Dato che "anna" ha il conto "test-1" con il flusso "alfa" attivo e una posizione aperta su "BTC"

  Scenario: Rimozione senza conferma sospesa
    Quando "anna" rimuove il conto "test-1" senza confermare
    Allora la rimozione è sospesa con il motivo "il conto ha flussi attivi o in pausa che verranno fermati: alfa"
    E il flusso "alfa" è nello stato "attivo"

  Scenario: Rimozione confermata ferma i flussi
    Quando "anna" rimuove il conto "test-1" confermando
    Allora sull'exchange la posizione su "BTC" è chiusa
    E il conto "test-1" non compare più tra i conti di "anna"
    E il flusso "alfa" compare tra i flussi archiviati di "anna"

  Scenario: Chiusura fallita blocca la rimozione
    Dato che l'exchange rifiuta la chiusura della posizione su "BTC" con il messaggio "Order rejected"
    Quando "anna" rimuove il conto "test-1" confermando
    Allora il conto "test-1" resta tra i conti di "anna"
    E il flusso "alfa" è nello stato "fermo"
    E l'esito riporta la posizione su "BTC" rimasta aperta con il motivo "Order rejected"
