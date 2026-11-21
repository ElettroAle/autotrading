# language: it
@R5.1.5
Funzionalità: R5.1.5 Forecast su orizzonti lunghi
  Come utente
  Voglio previsioni a giorni e settimane
  Perché un agente strategico ragiona su finestre lunghe

  La fonte "forecast" accetta come orizzonti anche 1 giorno e 1 settimana, oltre a 15 minuti e 1 ora (RF-08.05).
  Gli orizzonti lunghi si calcolano su candele giornaliere; ogni previsione si registra e riceve il prezzo
  effettivo allo scadere, come oggi, e partecipa alla valutazione del forecast (RF-26.01) e al grafico (R4.3.1).
  Lo storico più corto della profondità richiesta si dichiara.

  Contesto:
    Dato che il flusso "alfa" ha la fonte "forecast" sull'asset "BTC"

  Scenario: Previsione a 1 giorno
    Quando "anna" imposta l'orizzonte "1 giorno" e parte il ciclo
    Allora il contesto contiene la previsione di "BTC" a 1 giorno con il suo istante di riferimento

  Scenario: Previsione a 1 settimana
    Quando "anna" imposta l'orizzonte "1 settimana" e parte il ciclo
    Allora il contesto contiene la previsione di "BTC" a 1 settimana con il suo istante di riferimento

  Scenario: Storico giornaliero più corto della profondità richiesta
    Dato che per "BTC" sono disponibili solo 100 giorni di storico giornaliero
    Quando "anna" imposta l'orizzonte "1 settimana" e parte il ciclo
    Allora il contesto dichiara per "BTC" lo storico giornaliero ridotto a 100 giorni

  Scenario: Prezzo effettivo allo scadere
    Dato che ieri alle 10:00 è stata registrata una previsione a 1 giorno
    Quando passano le 10:00 di oggi
    Allora la previsione riceve il prezzo effettivo delle 10:00 di oggi
