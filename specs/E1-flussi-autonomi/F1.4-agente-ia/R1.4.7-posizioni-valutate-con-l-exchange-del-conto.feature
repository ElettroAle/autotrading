# language: it
@R1.4.7
Funzionalità: R1.4.7 Posizioni valutate con i prezzi dell'exchange del conto
  Come utente
  Voglio che l'agente valuti le posizioni aperte con prezzo e PnL dell'exchange del conto
  Perché le fonti di mercato possono leggere un'altra rete o un'altra piazza, con prezzi diversi da quelli a cui
  il flusso opera

  Ogni exchange dichiara, per ogni posizione aperta, il prezzo di mercato (mark price) con cui valuta la posizione e
  il PnL non realizzato. Le regole operative dicono all'agente che valuta e gestisce le posizioni aperte solo con
  questi valori; i dati delle fonti servono a stimare la direzione del mercato.

  Fuori ambito: il prezzo di mercato nelle pagine della dashboard, uno stop loss sull'exchange.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC" su un conto il cui exchange valuta BTC a 63400
    E che le fonti di mercato riportano per "BTC" il prezzo 64772

  Scenario: Il contesto mostra il prezzo dell'exchange del conto
    Dato che il flusso "alfa" ha una posizione short su "BTC" con prezzo di ingresso 63570 e PnL non realizzato 0,25 USDC
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene la posizione short su "BTC" con prezzo di mercato 63400 e PnL non realizzato 0,25 USDC

  Scenario: Le regole operative indicano il riferimento per le posizioni aperte
    Quando il flusso "alfa" esegue un ciclo
    Allora le regole operative dicono di valutare le posizioni aperte con prezzo di mercato e PnL non realizzato dell'exchange del conto
