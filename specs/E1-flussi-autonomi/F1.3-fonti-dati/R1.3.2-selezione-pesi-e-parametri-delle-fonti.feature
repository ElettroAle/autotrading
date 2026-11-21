# language: it
@R1.3.2
Funzionalità: R1.3.2 Selezione, pesi e parametri delle fonti per flusso
  Come utente
  Voglio scegliere per ogni flusso quali fonti attivare, con quale peso e con quali parametri
  Perché ogni flusso ragioni sui dati che ritengo utili, nell'importanza che ritengo giusta

  Una fonte attiva si interroga per ogni asset del flusso; una fonte non attiva non si interroga e non compare
  nel contesto. Il peso è un numero intero da 1 a 10; senza indicazione tutte le fonti attive hanno peso 5.
  I parametri non indicati assumono il valore predefinito del catalogo (R1.3.1); un parametro fuori dai valori
  ammessi rende la configurazione non valida.
  Selezione, pesi e parametri fanno parte della configurazione versionata del flusso (R1.1.3).
  L'agente tiene conto dei pesi nel ragionamento (RF-14.02): il segnaposto {source_weights} del system prompt (R1.4.8),
  presente nel predefinito, spiega il peso e riporta i pesi delle fonti attive. Quando le fonti sono in disaccordo
  prevale quella col peso più alto, non il numero dei segnali; i valori di una stessa fonte contano come una fonte
  sola; le istruzioni del flusso prevalgono sui pesi. Nessun calcolo sui pesi nel codice: decide il modello.

  Fuori ambito: la valutazione a posteriori della capacità predittiva delle fonti.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC, ETH"

  Scenario: Fonte attiva interrogata per ogni asset
    Dato che il flusso "alfa" ha attiva la fonte "pivot"
    Quando il flusso "alfa" esegue un ciclo
    Allora la fonte "pivot" è interrogata per "BTC" e per "ETH"

  Scenario: Fonte non attiva né interrogata né nel contesto
    Dato che il flusso "alfa" ha attive le fonti "indicatori" e non "notizie"
    Quando il flusso "alfa" esegue un ciclo
    Allora la fonte "notizie" non è interrogata
    E il contesto inviato all'agente non contiene notizie

  Scenario: Pesi predefiniti
    Dato che il flusso "alfa" ha attive le fonti "indicatori, sentiment-alternative-me" senza pesi
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto comunica all'agente il peso 5 per "indicatori" e per "sentiment-alternative-me"

  Scenario: Pesi indicati
    Dato che il flusso "alfa" ha attive le fonti "indicatori" con peso 8 e "sentiment-alternative-me" con peso 2
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto comunica all'agente il peso 8 per "indicatori" e 2 per "sentiment-alternative-me"

  Scenario: Parametro predefinito
    Dato che il flusso "alfa" ha attiva la fonte "notizie" senza parametri
    Quando il flusso "alfa" esegue un ciclo
    Allora la fonte "notizie" è interrogata con numero notizie 10 ed età massima 24 ore

  Scenario: Il system prompt predefinito spiega il peso
    Dato che il flusso "alfa" segue il system prompt predefinito
    E che il flusso "alfa" ha attive le fonti "forecast" con peso 10 e "indicatori" con peso 2
    Quando il flusso "alfa" esegue un ciclo
    Allora il system prompt inviato all'agente dice che il peso è un intero da 1 a 10, predefinito 5, importanza relativa data dall'utente a ogni fonte
    E dice che quando le fonti sono in disaccordo prevale quella col peso più alto, non il numero dei segnali
    E dice che più valori della stessa fonte contano come una fonte sola, col suo peso
    E dice che le istruzioni del flusso prevalgono sui pesi
    E chiede di nominare nel ragionamento di un'apertura la fonte che ha deciso la direzione quando le fonti erano in disaccordo
    E riporta i pesi "forecast 10, indicatori 2"

  Scenario: Regola del peso in un system prompt personalizzato
    Dato che il flusso "alfa" ha attive le fonti "forecast" con peso 10 e "indicatori" con peso 2
    E che il flusso "alfa" ha un system prompt personalizzato "Decidi con prudenza. {source_weights}"
    Quando il flusso "alfa" esegue un ciclo
    Allora il system prompt inviato all'agente contiene la regola del peso e i pesi "forecast 10, indicatori 2"

  Scenario: Fonti, pesi e parametri modificati creano una nuova versione
    Quando "anna" modifica il flusso "alfa" con peso 8 per la fonte "indicatori"
    Allora il flusso "alfa" ha la versione di configurazione 2 con la fonte "indicatori" di peso 8
    E la versione 1 del flusso "alfa" resta consultabile senza fonti

  Schema dello scenario: Peso o parametro non valido
    Quando "anna" modifica il flusso "alfa" con <valore>
    Allora la modifica è rifiutata con il motivo "<motivo>"

    Esempi:
      | valore                                   | motivo                                                       |
      | peso 0 per la fonte "indicatori"         | peso fuori da 1-10: indicatori                               |
      | peso 11 per la fonte "indicatori"        | peso fuori da 1-10: indicatori                               |
      | numero notizie 51 per la fonte "notizie" | parametro fuori dai valori ammessi: numero notizie, da 1 a 50 |
