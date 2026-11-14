# language: it
@R2.2.5
Funzionalità: R2.2.5 Posizioni chiuse del flusso
  Come utente
  Voglio consultare le posizioni chiuse di un flusso
  Perché veda il risultato di ogni operazione conclusa

  Per ogni posizione chiusa: asset, direzione, istanti e prezzi di apertura e di chiusura, PnL in valore e in
  percentuale, commissioni, motivo della chiusura (RF-23.04), come nello storico delle posizioni chiuse
  (R1.7.2), dalla più recente, a pagine di 50.

  Fuori ambito: i filtri per periodo e asset (R2.5.1).

  Contesto:
    Dato che il flusso "alfa" ha 60 posizioni chiuse, l'ultima long su "ETH" aperta a 3000 e chiusa a 3150 con PnL +15 USDC

  Scenario: Posizioni chiuse dalla più recente
    Quando "anna" apre le posizioni chiuse del flusso "alfa"
    Allora la prima riga è "ETH" con apertura 3000, chiusura 3150, PnL +15 USDC e +5,00%
    E la pagina mostra 50 posizioni con il comando per la pagina successiva

  Scenario: Nessuna posizione chiusa
    Dato che il flusso "beta" non ha posizioni chiuse
    Quando "anna" apre le posizioni chiuse del flusso "beta"
    Allora la pagina mostra "Nessuna posizione chiusa"
