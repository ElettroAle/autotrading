# language: it
@R1.3.3
Funzionalità: R1.3.3 Fonte indicatori tecnici
  Come utente
  Voglio che l'agente riceva prezzo e indicatori tecnici di ogni asset su due timeframe
  Perché valuti tendenza e momento del mercato sul breve e sul lungo periodo

  Per ogni asset la fonte fornisce prezzo corrente, mid price, open interest e funding rate correnti, e su due
  timeframe gli indicatori EMA20, MA20, MACD, RSI a 7 e a 14 periodi e volume.
  Il timeframe breve coincide con l'intervallo di ciclo del flusso; il timeframe lungo è di 4 ore e comprende in
  più le medie a 50 periodi (EMA50, MA50).
  Ogni indicatore si fornisce come valore corrente e come serie degli ultimi valori, 10 per impostazione
  predefinita. I valori si calcolano sui prezzi dell'exchange del conto del flusso.
  Parametri per flusso: lunghezza della serie, da 1 a 50, predefinito 10.

  Fuori ambito: livelli di Fibonacci, linee di Gann, analisi ciclica.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC", intervallo di ciclo di 15 minuti e la fonte "indicatori" attiva

  Scenario: Indicatori sul timeframe breve
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene per "BTC" sul timeframe di 15 minuti i valori correnti e le serie di 10 valori di:
      | indicatore |
      | EMA20      |
      | MA20       |
      | MACD       |
      | RSI7       |
      | RSI14      |
      | volume     |

  Scenario: Indicatori sul timeframe lungo
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene per "BTC" sul timeframe di 4 ore i valori correnti e le serie di 10 valori di:
      | indicatore |
      | EMA20      |
      | EMA50      |
      | MA20       |
      | MA50       |
      | MACD       |
      | RSI7       |
      | RSI14      |
      | volume     |

  Scenario: Valori correnti di mercato
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene per "BTC" prezzo corrente, mid price, open interest e funding rate

  Scenario: Valori calcolati sui prezzi dell'exchange
    Dato che l'exchange del conto riporta per "BTC" le chiusure a 15 minuti di una serie nota
    Quando il flusso "alfa" esegue un ciclo
    Allora il valore corrente di EMA20 per "BTC" sul timeframe di 15 minuti coincide con quello calcolato sulla serie nota

  Scenario: Lunghezza della serie configurata
    Dato che il flusso "alfa" ha la lunghezza della serie degli indicatori a 20
    Quando il flusso "alfa" esegue un ciclo
    Allora le serie degli indicatori per "BTC" hanno 20 valori
