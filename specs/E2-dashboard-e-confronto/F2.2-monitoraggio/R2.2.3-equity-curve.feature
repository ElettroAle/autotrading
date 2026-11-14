# language: it
@R2.2.3
Funzionalità: R2.2.3 Equity curve del flusso
  Come utente
  Voglio vedere l'andamento del valore di un flusso nel tempo
  Perché giudichi la strategia dal suo percorso e non solo dal risultato di oggi

  A ogni ciclo, concluso o fallito dopo la lettura dello stato, si registra l'equity del flusso: capitale
  allocato più PnL realizzato e non realizzato, meno le commissioni (R1.6.1). L'equity curve ha un punto per
  ciclo, con linea e area verdi sopra il capitale iniziale e rosse sotto (RF-23.01). L'utente sceglie il
  periodo: tutta la vita del flusso (predefinito), 7 giorni, 30 giorni o un intervallo libero.

  Fuori ambito: le curve sovrapposte di più flussi (R2.4.3); la ricostruzione dell'equity dei cicli precedenti a questa funzionalità.

  Contesto:
    Dato che il flusso "alfa" ha capitale iniziale 300 USDC
    E che i suoi ultimi tre cicli hanno registrato equity 310, 295 e 305 USDC

  Scenario: Punto di equity registrato a ogni ciclo
    Quando il flusso "alfa" conclude un ciclo con capitale allocato 300 USDC, PnL realizzato 4 USDC, PnL non realizzato 3 USDC e commissioni 1 USDC
    Allora il ciclo registra equity 306 USDC

  Scenario: Punto registrato anche per un ciclo fallito
    Quando un ciclo del flusso "alfa" fallisce dopo la lettura dello stato con equity 302 USDC
    Allora il ciclo registra equity 302 USDC

  Scenario: Colori sopra e sotto il capitale iniziale
    Quando "anna" apre l'equity curve del flusso "alfa"
    Allora i punti a 310 e 305 USDC sono nell'area verde
    E il punto a 295 USDC è nell'area rossa

  Scenario: Scelta del periodo
    Dato che il flusso "alfa" ha cicli negli ultimi 60 giorni
    Quando "anna" sceglie il periodo "30 giorni"
    Allora la curva mostra solo i punti degli ultimi 30 giorni

  Scenario: Flusso senza cicli
    Dato che il flusso "gamma" non ha ancora cicli
    Quando "anna" apre l'equity curve del flusso "gamma"
    Allora la pagina mostra "Nessun ciclo ancora eseguito"
