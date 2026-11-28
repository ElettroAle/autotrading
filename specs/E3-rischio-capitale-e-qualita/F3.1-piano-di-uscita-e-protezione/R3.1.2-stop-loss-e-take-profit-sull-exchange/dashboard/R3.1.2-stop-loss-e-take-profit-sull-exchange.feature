# language: it
@R3.1.2
Funzionalità: R3.1.2 Stop loss e take profit sull'exchange
  Come utente
  Voglio che ogni posizione aperta da un flusso abbia stop loss e take profit attivi sull'exchange
  Perché la posizione resta protetta tra un ciclo e l'altro, anche se la piattaforma è ferma

  Ogni flusso ha uno stop loss predefinito, obbligatorio: una percentuale di distanza dal prezzo d'ingresso, tra
  0,1 e 50, pari a 5 se non indicata. I flussi che esistono già ricevono 5. Il take profit predefinito è facoltativo:
  una percentuale maggiore di 0 dal prezzo d'ingresso, oppure assente. Modificarli crea una versione della
  configurazione (R1.1.3) e vale per le aperture successive.
  A ogni apertura la piattaforma piazza sull'exchange, sull'intera posizione, l'ordine di stop loss e, se c'è un
  obiettivo, l'ordine di take profit. Valgono i livelli del piano di uscita dell'agente (R3.1.1); dove mancano, i
  predefiniti del flusso calcolati sul prezzo d'ingresso reale (RF-18.06).
  Uno stop dell'agente più lontano dal prezzo d'ingresso dello stop predefinito si riporta allo stop predefinito, e
  il ciclo lo registra.
  Se l'exchange rifiuta l'ordine di stop loss, la posizione appena aperta si chiude subito e il ciclo ne registra il
  motivo. Se rifiuta solo il take profit, la posizione resta con il suo stop e il rifiuto si registra.
  Quando l'exchange esegue lo stop loss o il take profit, la chiusura è del flusso: entra nello storico delle
  posizioni chiuse con il motivo "stop loss" o "take profit" e con l'esito letto dall'exchange.
  Quando la posizione si chiude, per qualunque motivo, gli ordini di protezione rimasti si annullano.
  Una posizione aperta prima che il flusso avesse lo stop predefinito riceve lo stop loss al ciclo successivo.
  Una chiusura eseguita dall'exchange tra due cicli entra nello storico senza aspettare il ciclo successivo: un
  controllo periodico riconcilia i soli conti con posizioni dei flussi aperte, ogni intervallo di riconciliazione del
  conto, da 1 a 1440 minuti, predefinito 5. Vale per ogni exchange (Bug 778).

  Fuori ambito: lo spostamento dei livelli di una posizione aperta (R3.1.3); lo stop del flusso, che continua a
  chiudere le posizioni (R1.1.5); le notifiche di stop loss e take profit (R3.5.1).

  Scenario: Intervallo nella pagina del conto
    Dato che "anna" ha aperto la pagina del conto "principale"
    Quando imposta l'intervallo di riconciliazione a 15 minuti e salva
    Allora la pagina mostra l'intervallo di riconciliazione di 15 minuti
    E il campo ha il pulsante "Informazioni su Intervallo di riconciliazione (minuti)"
