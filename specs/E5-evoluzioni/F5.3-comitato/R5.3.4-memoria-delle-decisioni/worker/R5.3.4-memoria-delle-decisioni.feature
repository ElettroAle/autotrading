# language: it
@R5.3.4
Funzionalità: R5.3.4 Memoria del flusso
  Come utente
  Voglio accendere o spegnere la memoria di un flusso, regolarne l'ampiezza e leggere cosa contiene
  Perché l'agente ragioni in continuità con le proprie decisioni e io veda su cosa si basa

  La memoria è un'impostazione del flusso: attiva o non attiva, non attiva come predefinita. Se attiva, l'agente
  (unico, e il gestore del comitato quando esisterà) riceve nel contesto, per ogni asset, le proprie decisioni
  operative precedenti sullo stesso asset (apri, chiudi, inverti, modifica delle protezioni; non le decisioni di non
  agire) con l'esito ottenuto: istante, azione, prezzo, motivazione sintetica e PnL della posizione che ne è nata,
  realizzato se chiusa o non realizzato se aperta (RF-28.09). Si usano solo le decisioni del flusso stesso e solo
  quelle anteriori all'istante del ciclo (il replay userà la stessa regola).

  Ampiezza configurabile (decisione del proprietario, 24 novembre 2026): numero massimo di decisioni per asset e
  finestra in giorni, impostazioni del flusso con valori predefiniti 10 decisioni e 30 giorni.

  Consultazione. Con la memoria attiva, la pagina del flusso mostra la memoria: per ogni asset, ciò che l'agente
  riceverà al prossimo ciclo. Il dettaglio di ogni ciclo mostra la memoria che l'agente ha ricevuto in quel ciclo.
  Con la memoria non attiva la pagina del flusso non la mostra.

  Accendere, spegnere o regolare la memoria crea una nuova versione del flusso, come ogni altra impostazione.

  Scenario: Memoria attiva nel contesto
    Dato che il flusso "alfa" ha la memoria attiva
    E che "alfa" ha decisioni precedenti su "BTC"
    Quando parte il ciclo di "alfa"
    Allora il contesto contiene le decisioni precedenti su "BTC" con azione, prezzo, motivazione ed esito

  Scenario: Memoria non attiva
    Dato che il flusso "alfa" ha la memoria non attiva
    E che "alfa" ha decisioni precedenti su "BTC"
    Quando parte il ciclo di "alfa"
    Allora il contesto non contiene decisioni precedenti

  Scenario: Ampiezza della memoria
    Dato che il flusso "alfa" ha la memoria attiva con 2 decisioni e 7 giorni
    E che "alfa" ha 3 decisioni operative su "BTC" negli ultimi 7 giorni e una di 10 giorni fa
    Quando parte il ciclo di "alfa"
    Allora il contesto contiene solo le 2 decisioni più recenti su "BTC"

  Scenario: Solo decisioni operative
    Dato che il flusso "alfa" ha la memoria attiva
    E che "alfa" ha deciso di non agire su "BTC" nell'ultimo ciclo
    Quando parte il ciclo di "alfa"
    Allora la decisione di non agire non è nella memoria

  Scenario: Solo le decisioni del flusso stesso
    Dato che il flusso "alfa" ha la memoria attiva
    E che il flusso "beta" dello stesso conto ha decisioni su "BTC"
    Quando parte il ciclo di "alfa"
    Allora la memoria di "alfa" non contiene le decisioni di "beta"
