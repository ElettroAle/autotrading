# language: it
@R5.1.6
Funzionalità: R5.1.6 Tendenza su orizzonti lunghi negli indicatori
  Come utente
  Voglio che la fonte "indicatori" dia all'agente, per ogni asset, la variazione del prezzo su orizzonti di più giorni
  e il canale dei massimi e minimi giornalieri
  Perché le istruzioni del flusso possano seguire la tendenza di lungo periodo

  Un parametro della fonte "indicatori", "tendenza lunga", spento come predefinito, accende i valori. Si calcolano
  sulle candele giornaliere chiuse (giornata UTC) dello stesso adapter dei dati di mercato: variazione percentuale a
  7, 14, 30 e 60 giorni tra l'ultima chiusura giornaliera e quella di N giorni prima; massimo e minimo delle chiusure
  dei 20 giorni precedenti l'ultima; ultima chiusura giornaliera con il suo istante. Un orizzonte senza storico
  sufficiente compare tra i dati mancanti della fonte. Nessuna regola di apertura nella piattaforma: la regola resta
  nelle istruzioni del flusso.

  Scenario: I valori di tendenza arrivano all'agente quando il parametro è acceso
    Dato un flusso con la fonte indicatori e il parametro "tendenza lunga" a 1
    E 61 candele giornaliere chiuse disponibili per BTC
    Quando parte un ciclo
    Allora il contesto dell'agente contiene per BTC la variazione percentuale a 7, 14, 30 e 60 giorni
    E il massimo e il minimo delle chiusure dei 20 giorni precedenti l'ultima chiusura
    E l'ultima chiusura giornaliera con il suo istante

  Scenario: La variazione si calcola sulle chiusure giornaliere UTC
    Dato un flusso con la fonte indicatori e il parametro "tendenza lunga" a 1
    E che la chiusura giornaliera di 30 giorni fa è 50000 e l'ultima è 55000
    Quando parte un ciclo
    Allora la variazione a 30 giorni è 10

  Scenario: La candela del giorno in corso non conta
    Dato un flusso con la fonte indicatori e il parametro "tendenza lunga" a 1
    E che la giornata UTC corrente non è ancora chiusa
    Quando parte un ciclo
    Allora l'ultima chiusura giornaliera è quella della giornata precedente

  Scenario: Parametro spento come predefinito
    Dato un flusso con la fonte indicatori senza il parametro "tendenza lunga"
    Quando parte un ciclo
    Allora il contesto dell'agente non contiene i valori di tendenza lunga
    E la fonte non legge candele giornaliere

  Scenario: Storico insufficiente per un orizzonte
    Dato un flusso con la fonte indicatori e il parametro "tendenza lunga" a 1
    E un asset con solo 20 candele giornaliere chiuse
    Quando parte un ciclo
    Allora il contesto contiene le variazioni a 7 e 14 giorni
    E le variazioni a 30 e 60 giorni compaiono tra i dati mancanti
