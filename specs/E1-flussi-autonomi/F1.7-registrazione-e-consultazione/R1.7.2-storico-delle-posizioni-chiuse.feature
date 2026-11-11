# language: it
@R1.7.2 @wip
Funzionalità: R1.7.2 Storico delle posizioni chiuse
  Come utente
  Voglio consultare le posizioni chiuse di un flusso con il loro risultato
  Perché valuti come opera il flusso operazione per operazione

  Ogni posizione chiusa di un flusso conserva: asset, direzione, leva, prezzo di apertura e di chiusura,
  istante di apertura e di chiusura, durata, PnL in valore e in percentuale del margine, commissioni di apertura
  e chiusura, motivo della chiusura, cicli di apertura e di chiusura.
  In E1 i motivi di chiusura sono: decisione dell'agente, comando manuale, stop del flusso, rimozione del conto,
  chiusa fuori dalla piattaforma (comprese le liquidazioni).
  Lo storico è ordinato dalla chiusura più recente.

  Fuori ambito: chiusura per stop loss, take profit e incasso, filtri per periodo e asset.

  Contesto:
    Dato che "anna" ha il flusso "alfa"

  Scenario: Posizione chiusa dall'agente
    Dato che il flusso "alfa" ha aperto alle 10:00 una posizione long su "BTC" con leva 2 e margine 50 USDC al prezzo 100000
    E che l'agente l'ha chiusa alle 12:30 al prezzo 102000 con commissioni totali 0,08 USDC
    Quando "anna" consulta lo storico delle posizioni chiuse del flusso "alfa"
    Allora lo storico contiene la posizione long su "BTC" con leva 2, apertura 100000 e chiusura 102000
    E la posizione ha durata 2 ore e 30 minuti
    E la posizione ha PnL 2 USDC pari al 4% del margine e commissioni 0,08 USDC
    E la posizione ha motivo di chiusura "decisione dell'agente"

  Schema dello scenario: Motivi di chiusura
    Dato che una posizione del flusso "alfa" è stata chiusa per <evento>
    Quando "anna" consulta lo storico delle posizioni chiuse del flusso "alfa"
    Allora la posizione ha motivo di chiusura "<motivo>"

    Esempi:
      | evento                                | motivo                         |
      | chiusura manuale dell'utente          | comando manuale                |
      | stop del flusso                       | stop del flusso                |
      | rimozione del conto                   | rimozione del conto            |
      | liquidazione sull'exchange            | chiusa fuori dalla piattaforma |

  Scenario: Ordine dalla chiusura più recente
    Dato che il flusso "alfa" ha chiuso posizioni alle 09:00, alle 11:00 e alle 10:00
    Quando "anna" consulta lo storico delle posizioni chiuse del flusso "alfa"
    Allora lo storico elenca le posizioni chiuse alle 11:00, 10:00 e 09:00
