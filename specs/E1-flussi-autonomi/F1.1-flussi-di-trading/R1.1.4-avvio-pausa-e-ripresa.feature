# language: it
@R1.1.4
Funzionalità: R1.1.4 Avvio, pausa e ripresa di un flusso
  Come utente
  Voglio avviare un flusso, metterlo in pausa e riprenderlo
  Perché l'agente operi solo quando lo decido io

  Un flusso è in uno di questi stati: fermo, attivo, in pausa, archiviato.
  Solo un flusso attivo esegue cicli. In pausa il flusso non prende nuove decisioni e le sue posizioni restano
  aperte sull'exchange; alla ripresa riparte dal proprio stato, con le stesse posizioni e lo stesso capitale.
  Si avvia un flusso fermo; si mette in pausa un flusso attivo; si riprende un flusso in pausa.

  Fuori ambito: lo stop (R1.1.5), l'archiviazione (R1.1.6), la pausa automatica per errori permanenti (R1.2.4).

  Contesto:
    Dato che "anna" ha il flusso "alfa"

  @wip
  Scenario: Avvio di un flusso fermo
    Dato che il flusso "alfa" è fermo
    Quando "anna" avvia il flusso "alfa"
    Allora il flusso "alfa" è nello stato "attivo"
    E il flusso "alfa" esegue il primo ciclo all'avvio

  @wip
  Scenario: Pausa di un flusso attivo
    Dato che il flusso "alfa" è attivo con una posizione aperta su "BTC"
    Quando "anna" mette in pausa il flusso "alfa"
    Allora il flusso "alfa" è nello stato "in pausa"
    E il flusso "alfa" non esegue cicli
    E la posizione su "BTC" resta aperta sull'exchange

  @wip
  Scenario: Ripresa di un flusso in pausa
    Dato che il flusso "alfa" è in pausa con una posizione aperta su "BTC" e capitale allocato 400 USDC
    Quando "anna" riprende il flusso "alfa"
    Allora il flusso "alfa" è nello stato "attivo"
    E il flusso "alfa" ha ancora la posizione su "BTC" e capitale allocato 400 USDC

  Schema dello scenario: Comando non ammesso nello stato corrente
    Dato che il flusso "alfa" è nello stato "<stato>"
    Quando "anna" esegue sul flusso "alfa" il comando "<comando>"
    Allora il comando è rifiutato con il motivo "comando <comando> non ammesso per un flusso <stato>"

    Esempi:
      | stato      | comando   |
      | attivo     | avvia     |
      | in pausa   | avvia     |
      | fermo      | pausa     |
      | in pausa   | pausa     |
      | fermo      | riprendi  |
      | attivo     | riprendi  |
      | archiviato | avvia     |
