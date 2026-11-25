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

  Impostazione. Nel modulo del flusso la sezione «Memoria» sta subito dopo il modello, perché regola ciò che il modello
  riceve (decisione del proprietario, 25 novembre 2026).

  Consultazione. La memoria è un dettaglio da aprire su richiesta, non un dato della panoramica (decisione del
  proprietario, 25 novembre 2026): con la memoria attiva, la scheda «Decisioni» della pagina del flusso la offre in
  una sezione chiusa, «Memoria dell'agente», che aperta mostra per ogni asset ciò che l'agente riceverà al prossimo
  ciclo. Il dettaglio di ogni ciclo mostra la memoria che l'agente ha ricevuto in quel ciclo. Con la memoria non
  attiva la scheda «Decisioni» non la offre.

  Accendere, spegnere o regolare la memoria crea una nuova versione del flusso, come ogni altra impostazione.

  Scenario: Memoria non mostrata se non attiva
    Dato che il flusso "alfa" ha la memoria non attiva
    Quando "anna" apre le decisioni di "alfa"
    Allora la memoria non è mostrata

  Scenario: Memoria nelle decisioni, chiusa finché non si apre
    Dato che il flusso "alfa" ha la memoria attiva
    Quando "anna" apre le decisioni di "alfa"
    Allora la memoria è chiusa
    E aprendola vede ciò che l'agente riceverà al prossimo ciclo

  Scenario: Memoria ricevuta visibile nel ciclo
    Dato che il flusso "alfa" ha la memoria attiva
    Quando "anna" apre il dettaglio di un ciclo di "alfa"
    Allora vede la memoria che l'agente ha ricevuto in quel ciclo
