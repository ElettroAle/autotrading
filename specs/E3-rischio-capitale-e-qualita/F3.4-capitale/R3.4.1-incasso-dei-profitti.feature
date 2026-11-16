# language: it
@R3.4.1 @wip
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
  Scenario: Incasso al capitale allocato attuale
    Dato che "alfa" ha valore complessivo 620 USDC con una posizione aperta su "BTC"
    E che dopo la chiusura della posizione il valore di "alfa" è 618 USDC
    Quando "anna" incassa i profitti di "alfa"
    Allora la posizione di "alfa" su "BTC" è chiusa
    E il capitale allocato di "alfa" è 500 USDC
    E il capitale libero del conto "test-1" aumenta di 118 USDC
  Scenario: Incasso a un valore indicato
    Dato che "alfa" ha valore complessivo 618 USDC senza posizioni aperte
    Quando "anna" incassa i profitti di "alfa" portando il capitale allocato a 400 USDC
    Allora il capitale allocato di "alfa" è 400 USDC
    E il capitale libero del conto "test-1" aumenta di 218 USDC
  Schema dello scenario: Flusso senza profitti
    Dato che "alfa" ha valore complessivo <valore> USDC con una posizione aperta su "BTC"
    Quando "anna" incassa i profitti di "alfa"
    Allora il comando viene rifiutato con "alfa non ha profitti da incassare"
    E la posizione di "alfa" su "BTC" resta aperta
    Esempi:
      | valore |
      | 460    |
      | 500    |
  Schema dello scenario: Valore indicato non ammesso
    Dato che "alfa" ha valore complessivo 618 USDC senza posizioni aperte
    Quando "anna" incassa i profitti di "alfa" portando il capitale allocato a <valore> USDC
    Allora il comando viene rifiutato con "il capitale indicato è maggiore di 0 e minore del valore del flusso, 618 USDC"
    Esempi:
      | valore |
      | 0      |
      | 618    |
      | 700    |
  Scenario: Chiusura fallita
    Dato che "alfa" ha valore complessivo 620 USDC con una posizione aperta su "BTC"
    E che l'exchange rifiuta la chiusura su "BTC" con "Order rejected"
    Quando "anna" incassa i profitti di "alfa"
    Allora il capitale libero del conto "test-1" non cambia
    E l'esito riporta la posizione "BTC" non chiusa con "Order rejected"
  Scenario: Il flusso resta nel suo stato
    Dato che "alfa" ha valore complessivo 618 USDC senza posizioni aperte
    Quando "anna" incassa i profitti di "alfa"
    Allora il flusso "alfa" resta attivo
  Scenario: Motivo nello storico
    Dato che "alfa" ha valore complessivo 620 USDC con una posizione aperta su "BTC"
    Quando "anna" incassa i profitti di "alfa"
    Allora lo storico delle posizioni chiuse di "alfa" contiene "BTC" con motivo "incasso"
  Scenario: Conferma nella dashboard
    Dato che "alfa" ha valore complessivo 620 USDC con una posizione aperta su "BTC"
    Quando "anna" sceglie nella dashboard l'incasso dei profitti di "alfa"
    Allora la dashboard chiede conferma con "Chiudere 1 posizione di alfa e liberare circa 120 USDC?"
    E nessuna posizione viene chiusa finché "anna" non conferma
