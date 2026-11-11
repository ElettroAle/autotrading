# language: it
@R1.4.6 @wip
Funzionalità: R1.4.6 Costo delle chiamate al modello
  Come utente
  Voglio conoscere il costo di ogni chiamata al modello e il totale per flusso
  Perché confronti quanto mi costa ogni flusso

  Per ogni chiamata al modello si registrano token in ingresso, token in uscita e costo in USD, con il ciclo e
  il flusso. Il costo è quello riportato dal fornitore; se il fornitore non lo riporta, si calcola dai prezzi
  del catalogo, e se neppure quelli sono noti il costo si registra come non disponibile.
  Per ogni flusso è consultabile il costo totale dall'avvio e per giorno UTC.

  Fuori ambito: limiti di spesa sulla piattaforma, stima del costo prima del salvataggio della configurazione.

  Contesto:
    Dato che "anna" ha il flusso "alfa"

  Scenario: Costo riportato dal fornitore
    Dato che il fornitore riporta per la chiamata 2000 token in ingresso, 500 in uscita e costo 0,0031 USD
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra 2000 token in ingresso, 500 in uscita e costo 0,0031 USD

  Scenario: Costo calcolato dai prezzi del catalogo
    Dato che il fornitore non riporta il costo e riporta 1000 token in ingresso e 1000 in uscita
    E che il catalogo prezza il modello 1 USD per milione di token in ingresso e 2 USD per milione in uscita
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra costo 0,003 USD

  Scenario: Costo non disponibile
    Dato che né il fornitore né il catalogo riportano il prezzo
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra il costo come non disponibile

  Scenario: Totale per flusso
    Dato che il flusso "alfa" ha registrato 3 cicli con costo 0,01 USD ciascuno, 2 ieri e 1 oggi
    Quando "anna" consulta il costo del flusso "alfa"
    Allora il costo totale dall'avvio è 0,03 USD
    E il costo di ieri è 0,02 USD e quello di oggi 0,01 USD
