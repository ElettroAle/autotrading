# language: it
@R1.2.5 @wip
Funzionalità: R1.2.5 Fonte dati non disponibile
  Come utente
  Voglio che il ciclo prosegua anche se una fonte dati non risponde
  Perché l'agente decida con i dati disponibili invece di saltare il ciclo

  Le fonti attive di un flusso si interrogano in parallelo, con un tempo massimo di risposta pari a un quarto
  dell'intervallo di ciclo e mai oltre 60 secondi. Una fonte che non risponde in tempo o risponde con un errore
  è assente per quel ciclo: il contesto dichiara all'agente quali dati mancano e il ciclo registra la fonte
  assente con il motivo.
  Se tutte le fonti attive sono assenti il ciclo prosegue comunque, con il solo stato del flusso.

  Fuori ambito: la notifica di una fonte assente.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con intervallo di ciclo di 15 minuti e fonti "indicatori, notizie"

  Scenario: Una fonte non risponde
    Dato che la fonte "notizie" non risponde
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto inviato all'agente contiene i dati della fonte "indicatori"
    E il contesto dichiara mancanti i dati della fonte "notizie"
    E il ciclo registra la fonte "notizie" come assente con il motivo "nessuna risposta entro 60 secondi"
    E il ciclo prosegue fino alla decisione dell'agente

  Scenario: Tempo massimo di risposta per un intervallo breve
    Dato che il flusso "alfa" ha intervallo di ciclo di 2 minuti
    E che la fonte "notizie" risponde dopo 40 secondi
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra la fonte "notizie" come assente con il motivo "nessuna risposta entro 30 secondi"

  Scenario: Tutte le fonti assenti
    Dato che le fonti "indicatori" e "notizie" non rispondono
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto inviato all'agente contiene lo stato del flusso
    E il contesto dichiara mancanti i dati delle fonti "indicatori" e "notizie"
