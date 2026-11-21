# language: it
@R1.3.8
Funzionalità: R1.3.8 Valori raccolti registrati con il loro istante
  Come utente
  Voglio che ogni valore raccolto dalle fonti sia registrato con il suo istante di riferimento
  Perché i dati di ogni ciclo siano riusabili nei replay e nelle analisi

  Ogni valore raccolto da una fonte si registra con: fonte, asset (se la fonte è per asset), istante di
  riferimento del dato, istante di raccolta, ciclo e flusso che lo hanno raccolto.
  L'istante di riferimento è quello a cui il dato si riferisce (per esempio la chiusura della candela o la
  pubblicazione della notizia), distinto dall'istante di raccolta.

  Fuori ambito: il riuso degli stessi dati tra flussi diversi, il replay storico.

  Scenario: Valore registrato con i suoi istanti
    Dato che "anna" ha il flusso "alfa" con asset "BTC" e la fonte "indicatori" attiva
    E che l'ultima candela a 15 minuti di "BTC" chiude alle 10:00:00
    Quando il flusso "alfa" esegue alle 10:07:00 il ciclo "c-1"
    Allora i valori della fonte "indicatori" per "BTC" sono registrati con istante di riferimento 10:00:00
    E con istante di raccolta 10:07:00
    E con il ciclo "c-1" del flusso "alfa"

  Scenario: Notizia registrata con l'istante di pubblicazione
    Dato che "anna" ha il flusso "alfa" con la fonte "notizie" attiva
    E che una notizia è stata pubblicata alle 09:40:00
    Quando il flusso "alfa" esegue alle 10:07:00 il ciclo "c-1"
    Allora la notizia è registrata con istante di riferimento 09:40:00 e istante di raccolta 10:07:00
