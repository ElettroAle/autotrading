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

  Scenario: Opzioni e memoria dagli strumenti
    Quando il client MCP di "anna" accende il riepilogo della memoria di "alfa"
    Allora il dettaglio di "alfa" letto dagli strumenti riporta la memoria con il riepilogo acceso
    E la memoria di "alfa" letta dagli strumenti mostra le righe di riepilogo come le riceve l'agente
