# language: it
@R2.2.4
Funzionalità: R2.2.4 Posizioni aperte del flusso
  Come utente
  Voglio vedere le posizioni aperte di ogni flusso
  Perché sappia che cosa rischia ogni flusso in questo momento

  Per ogni posizione aperta del flusso: asset, direzione, leva, dimensione, prezzo di ingresso e PnL
  corrente in valore e in percentuale (RF-23.03), come nello stato del flusso (R1.6.1).

  Fuori ambito: l'exit plan, che arriva con il rischio avanzato (F3); la chiusura di emergenza (F3).

  Contesto:
    Dato che il flusso "alfa" ha una posizione long su "BTC" con leva 3, dimensione 0,01, prezzo di ingresso 60000 e PnL corrente +12 USDC

  Scenario: Elenco delle posizioni aperte
    Quando "anna" apre le posizioni del flusso "alfa"
    Allora vede "BTC" long, leva 3, dimensione 0,01, ingresso 60000, PnL +12 USDC

  Scenario: Nessuna posizione aperta
    Dato che il flusso "beta" non ha posizioni aperte
    Quando "anna" apre le posizioni del flusso "beta"
    Allora la pagina mostra "Nessuna posizione aperta"
