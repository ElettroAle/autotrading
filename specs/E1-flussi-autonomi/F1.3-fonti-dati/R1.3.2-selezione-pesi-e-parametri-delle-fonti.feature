# language: it
@R1.3.2 @wip
Funzionalità: R1.3.2 Selezione, pesi e parametri delle fonti per flusso
  Come utente
  Voglio scegliere per ogni flusso quali fonti attivare, con quale peso e con quali parametri
  Perché ogni flusso ragioni sui dati che ritengo utili, nell'importanza che ritengo giusta

  Una fonte attiva si interroga per ogni asset del flusso; una fonte non attiva non si interroga e non compare
  nel contesto. Il peso è un numero intero da 1 a 10; senza indicazione tutte le fonti attive hanno peso 5.
  I parametri non indicati assumono il valore predefinito del catalogo (R1.3.1); un parametro fuori dai valori
  ammessi rende la configurazione non valida.
  Selezione, pesi e parametri fanno parte della configurazione versionata del flusso (R1.1.3).

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
    Dato che il flusso "alfa" ha attive le fonti "indicatori, sentiment" senza pesi
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto comunica all'agente il peso 5 per "indicatori" e per "sentiment"

  Scenario: Pesi indicati
    Dato che il flusso "alfa" ha attive le fonti "indicatori" con peso 8 e "sentiment" con peso 2
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto comunica all'agente il peso 8 per "indicatori" e 2 per "sentiment"

  Scenario: Parametro predefinito
    Dato che il flusso "alfa" ha attiva la fonte "notizie" senza parametri
    Quando il flusso "alfa" esegue un ciclo
    Allora la fonte "notizie" è interrogata con numero notizie 10 ed età massima 24 ore

  Schema dello scenario: Peso o parametro non valido
    Quando "anna" modifica il flusso "alfa" con <valore>
    Allora la modifica è rifiutata con il motivo "<motivo>"

    Esempi:
      | valore                                 | motivo                                          |
      | peso 0 per la fonte "indicatori"       | peso fuori da 1-10: indicatori                  |
      | peso 11 per la fonte "indicatori"      | peso fuori da 1-10: indicatori                  |
      | numero notizie 51 per la fonte "notizie" | parametro fuori dai valori ammessi: numero notizie |
