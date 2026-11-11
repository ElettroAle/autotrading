# language: it
@R1.2.2 @wip
Funzionalità: R1.2.2 Nessuna sovrapposizione tra cicli dello stesso flusso
  Come utente
  Voglio che due cicli dello stesso flusso non siano mai in corso insieme
  Perché due decisioni non agiscano sullo stesso stato del flusso

  Se allo scadere dell'intervallo il ciclo precedente è ancora in corso, il ciclo previsto è saltato e il salto
  si registra con l'istante previsto. Il ciclo successivo resta pianificato al proprio istante.
  La regola vale anche tra più installazioni o processi che eseguono i cicli.

  Fuori ambito: la durata massima di un ciclo.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con intervallo di ciclo di 15 minuti e un ciclo previsto alle 10:22:00

  Scenario: Ciclo saltato perché il precedente è in corso
    Dato che il ciclo del flusso "alfa" iniziato alle 10:07:00 è ancora in corso alle 10:22:00
    Quando arrivano le 10:22:00
    Allora il ciclo delle 10:22:00 del flusso "alfa" è registrato come saltato
    E il prossimo ciclo del flusso "alfa" è previsto alle 10:37:00

  Scenario: Ciclo eseguito quando il precedente è concluso
    Dato che il ciclo del flusso "alfa" iniziato alle 10:07:00 si è concluso alle 10:10:00
    Quando arrivano le 10:22:00
    Allora il flusso "alfa" esegue il ciclo delle 10:22:00

  Scenario: Due esecutori non avviano lo stesso ciclo
    Dato che due esecutori dei cicli sono in funzione
    Quando arrivano le 10:22:00
    Allora il ciclo delle 10:22:00 del flusso "alfa" è eseguito una sola volta
