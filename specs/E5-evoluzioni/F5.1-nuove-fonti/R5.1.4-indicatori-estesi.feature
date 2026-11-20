# language: it
@R5.1.4
Funzionalità: R5.1.4 Indicatori estesi
  Come utente
  Voglio aggiungere livelli di Fibonacci, linee di Gann e analisi ciclica agli indicatori
  Perché alcune strategie si basano su questi strumenti

  La fonte "indicatori" offre tre nuovi indicatori selezionabili come parametri, calcolati dalle candele chiuse
  dell'exchange come gli altri (RF-06.04): livelli di ritracciamento di Fibonacci (23,6%, 38,2%, 50%, 61,8%,
  78,6%) tra minimo e massimo delle ultime N candele del timeframe lungo; angoli di Gann (1x1, 1x2, 2x1) dal
  minimo o massimo più recente delle ultime N candele; ciclo dominante (periodo in candele e fase) dalle ultime N
  candele. N è un parametro con predefinito 100. Uno storico più corto di N si dichiara.

  Contesto:
    Dato che il flusso "alfa" ha la fonte "indicatori" con l'asset "BTC"

  Scenario: Livelli di Fibonacci
    Dato che nelle ultime 100 candele a 4 ore il minimo è 50000 e il massimo è 60000
    Quando "anna" attiva l'indicatore "fibonacci" e parte il ciclo
    Allora il contesto contiene per "BTC" i livelli 57640, 56180, 55000, 53820 e 52140

  Scenario: Angoli di Gann e ciclo dominante
    Quando "anna" attiva gli indicatori "gann" e "ciclo" e parte il ciclo
    Allora il contesto contiene gli angoli di Gann 1x1, 1x2 e 2x1 e il ciclo dominante con periodo e fase

  Scenario: Storico insufficiente
    Dato che per "BTC" ci sono solo 60 candele a 4 ore
    Quando parte il ciclo con N uguale a 100
    Allora il contesto dichiara "storico di 60 candele, meno delle 100 richieste" e calcola sulle 60
