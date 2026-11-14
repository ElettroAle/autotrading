# language: it
@R2.2.2
Funzionalità: R2.2.2 Stato e riepilogo dei flussi
  Come utente
  Voglio vedere a colpo d'occhio stato e rendimento di ogni flusso
  Perché capisca subito quali flussi vanno bene e quali richiedono attenzione

  Per ogni flusso non archiviato la dashboard mostra: nome, stato (attivo, in pausa, fermo) con il motivo
  dell'eventuale pausa automatica, conto, ambiente, modello, ultima esecuzione con il suo esito, prossima
  esecuzione prevista, esito degli ultimi 10 cicli (RF-23.07), capitale iniziale, capitale attuale e
  rendimento complessivo in percentuale (RF-23.02). Il capitale attuale è quello dello stato del flusso
  (R1.6.1); un rendimento negativo è in rosso, uno positivo in verde.

  Fuori ambito: i flussi archiviati.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo sul conto "principale" con capitale iniziale 300 USDC e capitale attuale 330 USDC
    E che il flusso "beta" è in pausa automatica per "chiave del fornitore non valida"

  Scenario: Riepilogo di un flusso attivo
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "alfa" mostra stato "attivo", capitale iniziale 300 USDC, capitale attuale 330 USDC e rendimento +10,00% in verde
    E mostra ultima esecuzione, prossima esecuzione prevista ed esito degli ultimi 10 cicli

  Scenario: Flusso in pausa automatica
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "beta" mostra stato "in pausa" con il motivo "chiave del fornitore non valida"
    E non mostra una prossima esecuzione prevista

  Scenario: Rendimento negativo
    Dato che il flusso "alfa" ha capitale attuale 270 USDC
    Quando "anna" apre la pagina dei flussi
    Allora il flusso "alfa" mostra rendimento -10,00% in rosso
