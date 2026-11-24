# language: it
@R2.2.2
Funzionalità: R2.2.2 Stato e riepilogo dei flussi
  Come utente
  Voglio vedere a colpo d'occhio stato e rendimento di ogni flusso
  Perché capisca subito quali flussi vanno bene e quali richiedono attenzione

  Per ogni flusso non archiviato la dashboard mostra: nome, stato (attivo, in pausa, fermo) con il motivo
  dell'eventuale pausa automatica, conto, modello, asset della versione in vigore nell'ordine della
  configurazione (Bug 731), ultima esecuzione con il suo esito, prossima esecuzione
  prevista, capitale iniziale, capitale attuale e rendimento complessivo in percentuale (RF-23.02). L'esito degli
  ultimi 10 cicli e l'ambiente non sono più nella scheda: il riepilogo dei risultati li sostituisce (R6.4.2). Il
  capitale attuale è quello dello stato del flusso (R1.6.1); un rendimento negativo è in rosso, uno positivo in
  verde.

  Fuori ambito: i flussi archiviati.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo sul conto "principale" con capitale iniziale 300 USDC e capitale attuale 330 USDC
    E che il flusso "beta" è in pausa automatica per "chiave del fornitore non valida"

  Scenario: Riepilogo di un flusso attivo
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "alfa" mostra stato "attivo", capitale iniziale 300 USDC, capitale attuale 330 USDC e rendimento +10,00% in verde
    E mostra ultima esecuzione e prossima esecuzione prevista

  Scenario: Flusso in pausa automatica
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "beta" mostra stato "in pausa" con il motivo "chiave del fornitore non valida"
    E non mostra una prossima esecuzione prevista

  Scenario: Rendimento negativo
    Dato che il flusso "alfa" ha capitale attuale 270 USDC
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "alfa" mostra rendimento -10,00% in rosso

  Scenario: Conto, modello ed esito dell'ultima esecuzione
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "alfa" mostra conto "principale", modello "openai/gpt-4o" e ultima esecuzione "concluso"

  Scenario: Rendimento in pareggio in grigio
    Dato che il flusso "alfa" ha capitale attuale 300 USDC
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "alfa" mostra rendimento 0,00% in grigio

  Scenario: Asset di un flusso attivo
    Dato che il flusso "alfa" opera su "ETH", "SOL" e "BTC"
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "alfa" mostra gli asset "ETH · SOL · BTC" nell'ordine della configurazione

  Scenario: Bozza senza asset
    Dato una bozza "gamma" senza asset configurati
    Quando "anna" apre la pagina dei flussi
    Allora la bozza "gamma" mostra gli asset "nessuno"
