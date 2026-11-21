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

  Scenario: Ripresa confermata dall'utente
    Dato che le aperture di "alfa" sono sospese per perdita massima e il valore di "alfa" è 940 USDC
    Quando "anna" conferma la ripresa delle aperture di "alfa"
    Allora le aperture di "alfa" non sono sospese
    E il picco di "alfa" riparte da 940 USDC

  Scenario: Conferma senza sospensione
    Quando "anna" conferma la ripresa delle aperture di "alfa"
    Allora il comando viene rifiutato con "le aperture di alfa non sono sospese"

  Schema dello scenario: Soglia fuori dall'intervallo
    Quando "anna" imposta la perdita <soglia> di "alfa" a <valore>%
    Allora la modifica viene rifiutata con "la perdita massima va da 0,1 a 100"
    Esempi:
      | soglia               | valore |
      | giornaliera massima  | 0      |
      | giornaliera massima  | 101    |
      | massima dal picco    | 0      |
      | massima dal picco    | 101    |

  Scenario: Sospensione visibile nella dashboard
    Dato che le aperture di "alfa" sono sospese con motivo "perdita giornaliera 6% oltre il 5%"
    Quando "anna" apre il flusso "alfa" nella dashboard
    Allora la pagina mostra "aperture sospese: perdita giornaliera 6% oltre il 5%" e il comando "Riprendi le aperture"

  Scenario: Con ripresa il giorno dopo l'utente conferma prima
    Dato che "alfa" ha ripresa "il giorno dopo"
    E che le aperture di "alfa" sono sospese per perdita massima e il valore di "alfa" è 940 USDC
    Quando "anna" conferma la ripresa delle aperture di "alfa"
    Allora le aperture di "alfa" non sono sospese
    E il picco di "alfa" riparte da 940 USDC

  Scenario: La modifica di una soglia crea una versione
    Quando "anna" imposta la perdita giornaliera massima di "alfa" a 3%
    Allora la configurazione di "alfa" passa alla versione 2 con perdita giornaliera massima 3%

  Scenario: La modifica della ripresa crea una versione
    Quando "anna" imposta la ripresa di "alfa" a "il giorno dopo"
    Allora la configurazione di "alfa" passa alla versione 2 con ripresa "il giorno dopo"
