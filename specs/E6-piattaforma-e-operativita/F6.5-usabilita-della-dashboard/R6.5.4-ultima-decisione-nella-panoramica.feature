# language: it
@R6.5.4
Funzionalità: R6.5.4 Ultima decisione nella panoramica
  Come utente
  Voglio vedere nella panoramica del flusso l'ultima decisione dell'agente
  Perché capisco subito cosa ha deciso senza aprire il dettaglio del ciclo

  La scheda Panoramica del flusso mostra un riquadro con l'ultima decisione: istante dell'ultimo ciclo concluso con
  una decisione e, per ogni asset, azione, direzione, confidenza e il ragionamento accorciato, con il collegamento
  al dettaglio del ciclo. Il riquadro mostra l'ultima decisione a prescindere dal periodo scelto e lo dice. Senza
  cicli conclusi mostra «nessuna decisione ancora». Il dato è disponibile anche dall'interfaccia programmatica.

  Scenario: Ultima decisione mostrata
    Dato che l'ultimo ciclo concluso di "alfa", alle 10:00, ha deciso per BTC "apri long" con confidenza 72
    Quando "anna" apre la Panoramica del flusso "alfa"
    Allora vede l'ultima decisione delle 10:00 con BTC, "apri", "long", confidenza 72 e il ragionamento accorciato
    E un collegamento al dettaglio del ciclo delle 10:00

  Scenario: Ciclo fallito dopo l'ultima decisione
    Dato che il ciclo delle 11:00 di "alfa" è fallito prima della decisione
    Quando "anna" apre la Panoramica del flusso "alfa"
    Allora vede ancora la decisione del ciclo delle 10:00

  Scenario: Nessuna decisione
    Dato che il flusso "beta" non ha cicli conclusi
    Quando "anna" apre la Panoramica del flusso "beta"
    Allora il riquadro dice "nessuna decisione ancora"
