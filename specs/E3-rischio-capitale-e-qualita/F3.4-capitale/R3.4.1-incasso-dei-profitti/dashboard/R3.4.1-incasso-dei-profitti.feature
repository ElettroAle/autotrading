# language: it
@R3.4.1
Funzionalità: R3.4.1 Incasso dei profitti
  Come utente
  Voglio incassare con un solo comando i profitti di un flusso
  Perché metto al sicuro ciò che il flusso ha guadagnato e lo faccio ripartire dal capitale che scelgo

  Il comando si lancia dall'interfaccia programmatica e dalla dashboard, su un flusso (RF-22.04).
  La piattaforma chiude tutte le posizioni del flusso, poi porta il capitale allocato al valore indicato dall'utente,
  o al capitale allocato attuale se l'utente non indica un valore. La differenza tra il valore del flusso dopo le
  chiusure e il nuovo capitale allocato diventa capitale libero del conto.
  Se il valore complessivo del flusso non supera il capitale allocato, il flusso è in perdita o in pari: il comando
  non chiude nulla, non libera nulla e lo segnala.
  Un valore indicato deve essere maggiore di 0 e minore del valore complessivo del flusso.
  Se una chiusura fallisce, il comando non libera nulla e riporta le posizioni non chiuse con il motivo.
  Il flusso resta nello stato in cui era: un flusso attivo continua dal ciclo successivo.
  Ogni chiusura entra nello storico delle posizioni chiuse con il motivo "incasso".
  La dashboard chiede una conferma che mostra il profitto stimato al valore corrente.
  Fuori ambito: lo storico delle variazioni (R3.4.2); il rendimento dopo l'incasso (R3.4.3); il prelievo
  dall'exchange, che resta un'azione manuale dell'utente sull'exchange (RF-22.06).

  Contesto:
    Dato che "anna" ha sul conto "test-1" il flusso attivo "alfa" con capitale allocato 500 USDC
  Scenario: Conferma nella dashboard
    Dato che "alfa" ha valore complessivo 620 USDC con una posizione aperta su "BTC"
    Quando "anna" sceglie nella dashboard l'incasso dei profitti di "alfa"
    Allora la dashboard chiede conferma con "Chiudere 1 posizione di alfa e liberare circa 120 USDC?"
    E nessuna posizione viene chiusa finché "anna" non conferma
