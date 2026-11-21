# language: it
@R2.2.7
Funzionalità: R2.2.7 Cicli recenti e dettaglio del ciclo
  Come utente
  Voglio consultare i cicli di un flusso e tutto ciò che li ha prodotti
  Perché capisca perché l'agente ha deciso così

  La dashboard elenca i cicli del flusso dal più recente, a pagine di 50, con istante, esito e decisioni.
  Il dettaglio di un ciclo mostra tutto ciò che è registrato (R1.7.1): decisioni e ragionamento completo,
  contesto inviato e risposta integrale dell'agente, indicatori e previsioni, esito del rischio e ordini
  (RF-23.06).

  Fuori ambito: i filtri dello storico (R2.5.1).

  Contesto:
    Dato che il flusso "alfa" ha 120 cicli, l'ultimo concluso alle 10:07:00 con un'apertura long su "BTC"

  Scenario: Elenco dei cicli
    Quando "anna" apre i cicli del flusso "alfa"
    Allora il primo è quello delle 10:07:00 con esito concluso e decisione "apri long BTC"
    E la pagina mostra 50 cicli con il comando per la pagina successiva

  Scenario: Dettaglio di un ciclo
    Quando "anna" apre il ciclo delle 10:07:00
    Allora vede ragionamento completo, contesto inviato, risposta integrale, indicatori, previsioni, esito del rischio e ordine su "BTC"

  Scenario: Dettaglio di un ciclo fallito
    Dato che il ciclo delle 09:52:00 è fallito nel passo della decisione
    Quando "anna" apre il ciclo delle 09:52:00
    Allora vede il passo fallito, il motivo e ciò che il ciclo ha prodotto prima dell'errore
