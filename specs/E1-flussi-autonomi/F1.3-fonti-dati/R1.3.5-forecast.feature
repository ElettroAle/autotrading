# language: it
@R1.3.5
Funzionalità: R1.3.5 Fonte forecast
  Come utente
  Voglio che l'agente riceva una previsione del prezzo di ogni asset a 15 minuti e a 1 ora
  Perché tenga conto della direzione attesa del prezzo nel breve

  Per ogni asset e orizzonte la previsione riporta: ultimo prezzo, prezzo previsto, variazione percentuale
  prevista, orizzonte. Gli orizzonti sono 15 minuti e 1 ora.
  La previsione si calcola sullo storico dei prezzi dell'exchange; la profondità dello storico è un parametro del
  flusso, in giorni da 1 a 90, predefinito 7.
  Ogni previsione si registra; allo scadere dell'orizzonte si registra accanto il prezzo effettivo, per la
  valutazione dell'errore in un'epica successiva.
  Se lo storico disponibile è più corto della profondità richiesta, la previsione usa lo storico disponibile e il
  contesto lo dichiara.

  Fuori ambito: orizzonti di giorni o settimane, la valutazione dell'errore delle previsioni.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC" e la fonte "forecast" attiva

  @wip
  Scenario: Previsione sui due orizzonti
    Dato che l'ultimo prezzo di "BTC" è 100
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene per "BTC" una previsione a 15 minuti e una a 1 ora
    E ogni previsione riporta ultimo prezzo 100, prezzo previsto, variazione percentuale prevista e orizzonte

  @wip
  Scenario: Profondità dello storico predefinita
    Quando il flusso "alfa" esegue un ciclo
    Allora la previsione per "BTC" usa 7 giorni di storico

  @wip
  Scenario: Profondità dello storico configurata
    Dato che il flusso "alfa" ha la profondità dello storico del forecast a 30 giorni
    Quando il flusso "alfa" esegue un ciclo
    Allora la previsione per "BTC" usa 30 giorni di storico

  Scenario: Prezzo effettivo registrato allo scadere
    Dato che alle 10:00 il flusso "alfa" ha registrato per "BTC" una previsione a 15 minuti di 101
    Quando arrivano le 10:15 e il prezzo di "BTC" è 102
    Allora la previsione delle 10:00 per "BTC" a 15 minuti ha registrato il prezzo effettivo 102

  @wip
  Scenario: Storico più corto della profondità richiesta
    Dato che per "BTC" sono disponibili solo 3 giorni di storico
    Quando il flusso "alfa" esegue un ciclo
    Allora la previsione per "BTC" usa 3 giorni di storico
    E il contesto dichiara per "BTC" lo storico ridotto a 3 giorni
