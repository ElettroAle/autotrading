# language: it
@R2.5.2
Funzionalità: R2.5.2 Esportazione e importazione della configurazione
  Come utente
  Voglio esportare la strategia di un flusso in un file e importarla
  Perché la salvi, la riusi su un altro conto o la ricrei dopo un'archiviazione

  L'esportazione produce un file JSON con la sola strategia del flusso: intervallo, fonti con pesi e
  parametri, modello con i suoi parametri, istruzioni e regole di rischio (RF-21.06). Il file non contiene
  conto, capitale, asset, chiavi IA, cicli né altri dati del flusso. L'importazione di un file valido crea un
  nuovo flusso nello stato "bozza" (R2.4.1) alla versione 1, con nome scelto dall'utente; conto, capitale
  allocato e asset si assegnano prima dell'avvio, che verifica RF-02.05 come per ogni bozza. Un file non
  valido è rifiutato con il motivo, senza creare nulla. Disponibile dalla dashboard e dall'interfaccia
  programmatica.

  Fuori ambito: la condivisione tra utenti diversi.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC", fonti "indicatori" peso 2, modello "openrouter/deepseek-chat" e capitale 300 USDC sul conto "principale"

  Scenario: Esportazione della strategia
    Quando "anna" esporta il flusso "alfa"
    Allora ottiene un file con fonti "indicatori" peso 2 e modello "openrouter/deepseek-chat"
    E il file non contiene conto, capitale, asset né chiavi

  Scenario: Importazione in una bozza
    Dato che "anna" ha esportato il flusso "alfa"
    Quando "anna" importa il file con il nome "alfa bis"
    Allora esiste il flusso "alfa bis" nello stato "bozza" alla versione 1 con la strategia di "alfa"
    E non ha conto, capitale allocato né asset

  Scenario: Avvio della bozza importata
    Dato che "anna" ha importato il flusso "alfa bis"
    Quando "anna" assegna al flusso "alfa bis" il conto "principale", 100 USDC e l'asset "BTC"
    E "anna" avvia il flusso "alfa bis"
    Allora l'avvio è rifiutato perché "BTC" è già usato dal flusso "alfa" sul conto "principale"

  Scenario: File non valido
    Quando "anna" importa un file senza modello
    Allora l'importazione è rifiutata con il motivo "modello mancante"
    E nessun flusso viene creato

  Scenario: Modello non più disponibile
    Quando "anna" importa un file con un modello che non è nel catalogo
    Allora l'importazione è rifiutata con il motivo "modello non disponibile"
