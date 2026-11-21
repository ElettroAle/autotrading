# language: it
@R1.7.3
Funzionalità: R1.7.3 Consultazione di flussi e cicli
  Come utente
  Voglio consultare i miei flussi e i loro cicli tramite l'interfaccia programmatica
  Perché segua l'andamento dei flussi senza dashboard

  L'utente consulta:
  - l'elenco dei suoi flussi in uso, ciascuno con nome, conto, ambiente, stato, motivo dell'eventuale pausa
    automatica, modello, ultimo ciclo con il suo esito e prossimo ciclo previsto;
  - lo stato di un flusso (R1.6.1);
  - i cicli di un flusso, dal più recente, a pagine di 50, ciascuno con istante, esito e decisioni;
  - il dettaglio di un ciclo con tutto ciò che è registrato (R1.7.1).
  Ogni consultazione riguarda solo i flussi dell'utente.
  Letture dello stesso conto dall'API entro 10 secondi riusano l'ultima lettura riuscita; una lettura non vale mai per
  un altro tenant o un altro conto, e un errore non si riusa; i cicli leggono sempre dall'exchange.

  Fuori ambito: la dashboard, i filtri dello storico per periodo, asset o configurazione.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con intervallo di 15 minuti e 120 cicli registrati, l'ultimo concluso alle 10:07:00
    E che "bruno" ha il flusso "omega"

  Scenario: Elenco dei flussi
    Quando "anna" consulta i propri flussi
    Allora l'elenco contiene il flusso "alfa" nello stato "attivo" con ultimo ciclo alle 10:07:00 concluso e prossimo ciclo alle 10:22:00
    E l'elenco non contiene il flusso "omega"

  Scenario: Elenco dei flussi con conto, ambiente, pausa automatica e modello
    Dato che "anna" ha il flusso "beta" in pausa automatica con il motivo "credito esaurito presso openrouter"
    Quando "anna" consulta i propri flussi
    Allora l'elenco contiene il flusso "beta" con conto "test-1", ambiente "dev", stato "in pausa", motivo della pausa "credito esaurito presso openrouter" e modello "openrouter/deepseek-chat"

  Scenario: Cicli a pagine
    Quando "anna" consulta la prima pagina dei cicli del flusso "alfa"
    Allora la pagina contiene 50 cicli dal più recente
    E ogni ciclo riporta istante, esito e decisioni

  Scenario: Dettaglio di un ciclo
    Quando "anna" consulta il dettaglio dell'ultimo ciclo del flusso "alfa"
    Allora il dettaglio contiene il contesto inviato all'agente, la risposta integrale e gli ordini con il loro esito

  Scenario: Flusso di un altro utente
    Quando "anna" consulta i cicli del flusso "omega"
    Allora la consultazione risponde che il flusso non esiste

  Scenario: Letture dello stesso conto entro 10 secondi
    Dato che "anna" consulta il conto "test-1" dall'API
    Quando "anna" consulta di nuovo il conto "test-1" dall'API dopo 9 secondi
    Allora l'exchange ha letto il conto "test-1" 1 volta
    E le due consultazioni riportano la stessa lettura

  Scenario: Nuova lettura dopo 10 secondi
    Dato che "anna" consulta il conto "test-1" dall'API
    Quando "anna" consulta di nuovo il conto "test-1" dall'API dopo 10 secondi
    Allora l'exchange ha letto il conto "test-1" 2 volte

  Scenario: Tenant e conti diversi non condividono la lettura
    Dato che "anna" consulta il conto "test-1" dall'API
    Quando "anna" consulta il conto "test-2" dall'API
    E "bruno" consulta il conto "test-1" dall'API
    Allora l'exchange ha letto il conto "test-1" 2 volte
    E l'exchange ha letto il conto "test-2" 1 volta

  Scenario: Una lettura fallita non si riusa
    Dato che l'exchange non risponde alla lettura del conto "test-1"
    E che "anna" consulta il conto "test-1" dall'API
    Quando l'exchange torna a rispondere
    E "anna" consulta di nuovo il conto "test-1" dall'API dopo 1 secondo
    Allora la prima consultazione risponde che l'exchange non è raggiungibile e la seconda riporta la lettura
    E l'exchange ha letto il conto "test-1" 2 volte
