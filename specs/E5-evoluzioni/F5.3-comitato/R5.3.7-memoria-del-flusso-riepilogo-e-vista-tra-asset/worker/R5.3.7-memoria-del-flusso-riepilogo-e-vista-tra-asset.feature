# language: it
@R5.3.7
Funzionalità: R5.3.7 Memoria del flusso: riepilogo e vista tra asset
  Come utente
  Voglio poter aggiungere alla memoria un riepilogo dei risultati per asset e direzione, e la vista degli stessi
  risultati sugli altri asset del flusso
  Perché l'agente non debba contare da solo quante aperture ha perso in una direzione e veda, sull'asset che sta
  valutando, che cosa è appena successo sugli altri asset del flusso

  Seguito di R5.3.4 e R5.3.5: la memoria del flusso è un elenco di decisioni per asset.

  Opzioni della memoria, spente di default; valgono quando la memoria è attiva. Con le due spente la memoria è quella
  di oggi.
  - Riepilogo: in testa alla memoria di ogni asset, una riga per ogni direzione in cui il flusso ha posizioni chiuse su
    quell'asset nei giorni della memoria.
  - Altri asset: nella memoria di ogni asset, dopo il riepilogo, le righe di riepilogo degli altri asset del flusso.
    Non porta le decisioni degli altri asset.

  Regole.
  - La riga conta le posizioni chiuse, non le decisioni, e non è limitata dal numero di decisioni della memoria.
  - Forma della riga: «<asset> <direzione> — oggi: <n> chiuse, <n> vinte, <n> perse, PnL <importo> <valuta>; ultimi
    <giorni della memoria> giorni: <n> chiuse, <n> vinte, <n> perse, PnL <importo> <valuta>». Oggi è il giorno corrente
    UTC.
  - Vinta: PnL al netto delle commissioni sopra zero. Persa: sotto zero. Una posizione in pari conta solo tra le
    chiuse.
  - Una direzione senza posizioni chiuse nei giorni della memoria non ha riga.
  - La memoria letta dall'utente (API, MCP, dashboard) mostra riepilogo e altri asset come li riceve l'agente.

  I flussi esistenti non ricevono una versione nuova della configurazione.

  Fuori ambito: riepilogo tra flussi diversi, statistiche diverse da quelle della riga.

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "NEAR" e "SUI" e la memoria attiva con 2 giorni
    E che "alfa" ha chiuso su "NEAR" queste posizioni short, con PnL al netto delle commissioni:
      | quando | PnL   |
      | oggi   | -2,40 |
      | oggi   | -2,40 |
      | oggi   | -1,47 |
      | ieri   | 3,31  |
      | ieri   | 1,86  |
    E che "alfa" ha chiuso oggi su "SUI" una posizione short con PnL netto -0,81 USDC

  Scenario: Riga di riepilogo in testa alla memoria
    Dato che la memoria di "alfa" ha il riepilogo acceso
    Quando parte il ciclo di "alfa"
    Allora la memoria di "NEAR" comincia con "NEAR short — oggi: 3 chiuse, 0 vinte, 3 perse, PnL -6,27 USDC; ultimi 2 giorni: 5 chiuse, 2 vinte, 3 perse, PnL -1,10 USDC"
    E dopo la riga seguono le decisioni su "NEAR" come oggi

  Scenario: Direzione senza posizioni chiuse
    Dato che la memoria di "alfa" ha il riepilogo acceso
    Quando parte il ciclo di "alfa"
    Allora la memoria di "NEAR" non ha una riga di riepilogo per long

  Scenario: Posizione in pari
    Dato che la memoria di "alfa" ha il riepilogo acceso
    E che "alfa" ha chiuso oggi su "NEAR" un'altra posizione short con PnL netto 0 USDC
    Quando parte il ciclo di "alfa"
    Allora la memoria di "NEAR" comincia con "NEAR short — oggi: 4 chiuse, 0 vinte, 3 perse, PnL -6,27 USDC; ultimi 2 giorni: 6 chiuse, 2 vinte, 3 perse, PnL -1,10 USDC"

  Scenario: Il riepilogo non dipende dal numero di decisioni della memoria
    Dato che la memoria di "alfa" ha il riepilogo acceso e 2 decisioni
    Quando parte il ciclo di "alfa"
    Allora la memoria di "NEAR" comincia con "NEAR short — oggi: 3 chiuse, 0 vinte, 3 perse, PnL -6,27 USDC; ultimi 2 giorni: 5 chiuse, 2 vinte, 3 perse, PnL -1,10 USDC"

  Scenario: Altri asset del flusso
    Dato che la memoria di "alfa" ha gli altri asset accesi e il riepilogo spento
    Quando parte il ciclo di "alfa"
    Allora la memoria di "NEAR" riporta tra gli altri asset "SUI short — oggi: 1 chiuse, 0 vinte, 1 perse, PnL -0,81 USDC; ultimi 2 giorni: 1 chiuse, 0 vinte, 1 perse, PnL -0,81 USDC"
    E la memoria di "NEAR" non riporta le decisioni su "SUI"
    E la memoria di "NEAR" non comincia con una riga di riepilogo di "NEAR"

  Scenario: Opzioni spente
    Dato che la memoria di "alfa" ha il riepilogo spento e gli altri asset spenti
    Quando parte il ciclo di "alfa"
    Allora la memoria di "NEAR" contiene solo le decisioni su "NEAR", come oggi
