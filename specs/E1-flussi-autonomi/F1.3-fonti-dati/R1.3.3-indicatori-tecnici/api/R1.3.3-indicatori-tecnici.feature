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

  Schema dello scenario: Lunghezza della serie fuori dall'intervallo
    Quando "anna" imposta sul flusso "alfa" la fonte "indicatori" con lunghezza serie <valore>
    Allora la modifica è rifiutata con il motivo "parametro fuori dai valori ammessi: lunghezza serie, da 1 a 50"

    Esempi:
      | valore |
      | 0      |
      | 51     |
