# language: it
@R3.2.2
Funzionalità: R3.2.2 Perdita massima del flusso
  Come utente
  Voglio che un flusso smetta di aprire posizioni quando perde oltre una soglia
  Perché una giornata o una fase negativa non consuma tutto il capitale del flusso

  Ogni flusso può avere due soglie di perdita massima, facoltative, ciascuna da 0,1 a 100 (RF-18.08):
  - giornaliera: perdita percentuale del valore del flusso rispetto al valore che aveva alle 00:00 UTC del giorno;
  - dal picco: perdita percentuale rispetto al valore più alto raggiunto dal flusso dall'avvio o dall'ultima ripresa.
  Il valore del flusso è il suo valore complessivo (R1.6.1), letto a ogni ciclo. Aumenti, riduzioni e incassi del
  capitale non sono perdite né guadagni: i valori di riferimento si spostano dello stesso importo.
  Superata una soglia, le aperture del flusso sono sospese: le aperture decise dall'agente non si eseguono e il ciclo
  ne registra il motivo. I cicli continuano; chiusure e aggiornamenti del piano di uscita si eseguono. L'utente viene
  avvisato una volta per sospensione (R1.8.2).
  Per ogni flusso l'utente sceglie la ripresa: "manuale" (predefinita), cioè le aperture riprendono quando l'utente
  lo conferma dall'interfaccia programmatica o dalla dashboard; oppure "il giorno dopo", cioè riprendono da sole alle
  00:00 UTC del giorno successivo, e l'utente può comunque confermare prima. A ogni ripresa il picco riparte dal
  valore del flusso in quel momento.
  La dashboard mostra sul flusso la sospensione, la soglia superata e il comando di ripresa.
  Modificare soglie e ripresa crea una versione della configurazione (R1.1.3).
  Fuori ambito: la chiusura automatica delle posizioni, che restano all'agente e ai loro stop loss (R3.1.2).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC", perdita giornaliera massima 5%, perdita massima dal picco 10% e ripresa "manuale"

  Scenario: Perdita giornaliera oltre la soglia
    Dato che alle 00:00 UTC di oggi il valore di "alfa" era 1000 USDC
    Quando un ciclo di "alfa" legge il valore 940 USDC
    Allora le aperture di "alfa" sono sospese con motivo "perdita giornaliera 6% oltre il 5%"
    E "anna" riceve la notifica "⏸️ alfa: aperture sospese" con le righe "Motivo: perdita giornaliera 6% oltre il 5%"

  Scenario: Perdita dal picco oltre la soglia
    Dato che il valore più alto raggiunto da "alfa" è 1200 USDC
    E che alle 00:00 UTC di oggi il valore di "alfa" era 1100 USDC
    Quando un ciclo di "alfa" legge il valore 1068 USDC
    Allora le aperture di "alfa" sono sospese con motivo "perdita dal picco 11% oltre il 10%"

  Scenario: Perdita entro le soglie
    Dato che alle 00:00 UTC di oggi il valore di "alfa" era 1000 USDC e il valore più alto raggiunto è 1000 USDC
    Quando un ciclo di "alfa" legge il valore 960 USDC
    Allora le aperture di "alfa" non sono sospese

  Scenario: Apertura decisa durante la sospensione
    Dato che le aperture di "alfa" sono sospese per perdita massima
    Quando l'agente di "alfa" decide di aprire long su "BTC"
    Allora "alfa" non apre la posizione su "BTC"
    E il ciclo di "alfa" registra "apertura BTC non eseguita: aperture sospese per perdita massima"

  Scenario: Chiusura decisa durante la sospensione
    Dato che le aperture di "alfa" sono sospese per perdita massima
    E che "alfa" ha una posizione aperta su "BTC"
    Quando l'agente di "alfa" decide di chiudere la posizione su "BTC"
    Allora "alfa" chiude la posizione su "BTC"

  Scenario: Un solo avviso per sospensione
    Dato che le aperture di "alfa" sono sospese per perdita massima e "anna" ne ha ricevuto la notifica
    Quando parte il ciclo successivo di "alfa" con la soglia ancora superata
    Allora "anna" non riceve un'altra notifica di sospensione

  Scenario: Con ripresa manuale il giorno dopo resta sospeso
    Dato che le aperture di "alfa" sono sospese per perdita massima
    Quando arrivano le 00:00 UTC del giorno successivo
    Allora le aperture di "alfa" restano sospese

  Scenario: Ripresa il giorno dopo
    Dato che "alfa" ha ripresa "il giorno dopo"
    E che le aperture di "alfa" sono sospese per perdita massima e il valore di "alfa" è 940 USDC
    Quando arrivano le 00:00 UTC del giorno successivo
    Allora le aperture di "alfa" non sono sospese
    E il picco di "alfa" riparte da 940 USDC

  Scenario: Una riduzione del capitale non è una perdita
    Dato che alle 00:00 UTC di oggi il valore di "alfa" era 1000 USDC
    Quando "anna" riduce di 200 USDC il capitale allocato di "alfa" e un ciclo legge il valore 800 USDC
    Allora le aperture di "alfa" non sono sospese
