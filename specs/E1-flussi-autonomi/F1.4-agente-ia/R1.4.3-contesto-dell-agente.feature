# language: it
@R1.4.3
Funzionalità: R1.4.3 Contesto inviato all'agente
  Come utente
  Voglio che l'agente riceva a ogni ciclo un contesto completo del flusso
  Perché decida con le mie istruzioni, lo stato del flusso e i dati delle fonti attive

  Il contesto comprende:
  - le istruzioni dell'agente del flusso (ruolo, obiettivo, strategia) e le regole operative vigenti;
  - l'ora corrente e il tempo trascorso dall'avvio del flusso;
  - lo stato del flusso: capitale allocato, liquidità disponibile, valore complessivo, rendimento percentuale
    dall'avvio, posizioni aperte con asset, direzione, dimensione, leva, prezzo di ingresso, PnL non realizzato
    e prezzo di liquidazione;
  - i dati delle fonti attive per ogni asset e i pesi delle fonti;
  - i dati mancanti, dichiarati (R1.2.5).
  Le regole operative vigenti sono: al massimo una posizione per asset, azioni ammesse apri, chiudi e mantieni,
  leva da 1 alla leva massima del flusso, formato obbligatorio della risposta.
  Il contesto riguarda solo il flusso: non contiene saldo, posizioni o dati di altri flussi né credenziali.

  Fuori ambito: la memoria delle decisioni precedenti, la narrativa di un agente strategico.

  Contesto:
    Dato che "anna" ha il flusso "alfa" avviato alle 08:00 con asset "BTC, ETH", leva massima 5 e istruzioni "Sei un trader prudente"
    E che "anna" ha anche il flusso "beta" sullo stesso conto con asset "SOL"

  Scenario: Istruzioni e regole operative
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene le istruzioni "Sei un trader prudente"
    E il contesto contiene le regole operative con leva ammessa da 1 a 5

  Scenario: Ora e tempo trascorso
    Quando il flusso "alfa" esegue un ciclo alle 10:30
    Allora il contesto contiene l'ora corrente 10:30 e il tempo trascorso dall'avvio di 2 ore e 30 minuti

  Scenario: Stato del flusso
    Dato che il flusso "alfa" ha capitale allocato 400 USDC, liquidità disponibile 250 USDC e una posizione long su "BTC" con leva 3
    E che il flusso "alfa" ha un rendimento dall'avvio del 2,5%
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene capitale allocato 400 USDC e liquidità disponibile 250 USDC
    E il contesto contiene il rendimento dall'avvio del 2,5%
    E il contesto contiene la posizione long su "BTC" con dimensione, leva 3, prezzo di ingresso, PnL non realizzato e prezzo di liquidazione

  Scenario: Solo il flusso, mai gli altri
    Dato che il flusso "beta" ha una posizione aperta su "SOL"
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto non contiene la posizione su "SOL"
    E il contesto non contiene il saldo del conto
