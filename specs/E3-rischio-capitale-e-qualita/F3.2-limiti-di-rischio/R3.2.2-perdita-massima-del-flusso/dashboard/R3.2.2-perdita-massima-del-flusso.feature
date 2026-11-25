# language: it
@R3.2.2
Funzionalità: R3.2.2 Perdita massima del flusso
  Come utente
  Voglio che un flusso smetta di aprire posizioni quando perde oltre una soglia
  Perché una giornata o una fase negativa non consuma tutto il capitale del flusso

  Ogni flusso può avere due soglie di perdita massima, facoltative, ciascuna da 0,1 a 100 (RF-18.08):
  - giornaliera: perdita percentuale del valore del flusso rispetto al valore che aveva alle 00:00 UTC del giorno o,
    se le aperture sono riprese dopo, al momento dell'ultima ripresa (Bug 775);
  - dal picco: perdita percentuale rispetto al valore più alto raggiunto dal flusso dall'avvio o dall'ultima ripresa.
  Il valore del flusso è il suo valore complessivo (R1.6.1), letto a ogni ciclo. Aumenti, riduzioni e incassi del
  capitale non sono perdite né guadagni: i valori di riferimento si spostano dello stesso importo.
  Superata una soglia, le aperture del flusso sono sospese: le aperture decise dall'agente non si eseguono e il ciclo
  ne registra il motivo. I cicli continuano; chiusure e aggiornamenti del piano di uscita si eseguono. L'utente viene
  avvisato una volta per sospensione (R1.8.2).
  Per ogni flusso l'utente sceglie la ripresa: "manuale" (predefinita), cioè le aperture riprendono quando l'utente
  lo conferma dall'interfaccia programmatica o dalla dashboard; oppure "il giorno dopo", cioè riprendono da sole alle
  00:00 UTC del giorno successivo, e l'utente può comunque confermare prima. A ogni ripresa il picco e la perdita
  giornaliera ripartono dal valore del flusso in quel momento.
  La dashboard mostra sul flusso la sospensione, la soglia superata e il comando di ripresa.
  Modificare soglie e ripresa crea una versione della configurazione (R1.1.3).
  Fuori ambito: la chiusura automatica delle posizioni, che restano all'agente e ai loro stop loss (R3.1.2).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC", perdita giornaliera massima 5%, perdita massima dal picco 10% e ripresa "manuale"

  Scenario: Sospensione visibile nella dashboard
    Dato che le aperture di "alfa" sono sospese con motivo "perdita giornaliera 6% oltre il 5%"
    Quando "anna" apre il flusso "alfa" nella dashboard
    Allora la pagina mostra "aperture sospese: perdita giornaliera 6% oltre il 5%" e il comando "Riprendi le aperture"
