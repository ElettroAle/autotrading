# language: it
@R6.4.1
Funzionalità: R6.4.1 Dashboard leggibile su mobile
  Come utente
  Voglio usare la dashboard dal telefono senza testi tagliati e con azioni chiare
  Perché controllo i flussi anche fuori casa

  Ritocchi mirati dall'analisi UI/UX del 15/11/2026 a 360 pixel: il disegno attuale resta, si correggono solo i
  punti non ottimizzati. Le liste etichetta-valore vanno a capo anche con parole lunghe senza spazi (nomi dei
  modelli, indirizzi): nessuna pagina scorre in orizzontale. Nella pagina del flusso le viste (posizioni aperte e
  chiuse, cicli, versioni) compaiono come schede o comandi riconoscibili, separate dall'azione Modifica; tra i
  comandi Avvia risalta come principale e Archivia, nelle impostazioni del flusso (Bug 560), come distruttivo; stato
  e risultati vengono prima della configurazione; il titolo è il nome del flusso; l'avviso della rete non ripete la
  parola. Le sottopagine di un flusso (cicli, posizioni, versioni, modifica) mostrano di quale flusso sono. Nello
  storico ogni filtro ha l'etichetta sopra il suo campo. La pagina Notifiche spiega come collegare Telegram. Il
  confronto delle versioni è disattivato con una sola versione. Su schermi larghi l'aspetto attuale resta. La
  legenda degli esiti dei cicli recenti nell'elenco dei flussi è tolta con la loro fila (R6.4.2).

  Scenario: Nessuno scorrimento orizzontale
    Dato uno schermo largo 360 pixel
    Quando l'utente apre una qualsiasi pagina della dashboard
    Allora la pagina non scorre in orizzontale

  Scenario: Parole lunghe a capo
    Dato uno schermo largo 360 pixel
    E il flusso "prova-btc" con il modello "openrouter/~deepseek/deepseek-flash-latest"
    Quando l'utente apre la pagina del flusso
    Allora il nome del modello resta entro il riquadro ed è leggibile per intero

  Scenario: Viste e comandi del flusso riconoscibili
    Dato uno schermo largo 360 pixel
    Quando l'utente apre la pagina del flusso "prova-btc"
    Allora posizioni, cicli e versioni compaiono come schede o comandi separati da Modifica
    E Avvia risalta come comando principale e Archivia come distruttivo

  Scenario: Stato prima della configurazione
    Quando l'utente apre la pagina del flusso "prova-btc"
    Allora il titolo è "prova-btc" e lo stato viene prima della configurazione

  Scenario: Sottopagina con il nome del flusso
    Quando l'utente apre i cicli del flusso "prova-btc"
    Allora la pagina mostra che sono i cicli di "prova-btc"

  Scenario: Filtri dello storico
    Dato uno schermo largo 360 pixel
    Quando l'utente apre lo storico
    Allora ogni filtro ha la sua etichetta sopra il proprio campo

  Scenario: Confronto con una sola versione
    Dato che il flusso "prova-btc" ha una sola versione
    Quando l'utente apre le versioni della configurazione
    Allora il comando Confronta è disattivato

  Scenario: Come collegare Telegram
    Dato che l'utente non ha collegato Telegram
    Quando apre la pagina Notifiche
    Allora legge i passi per collegare la chat con il codice

  Scenario: Schermi larghi invariati
    Dato uno schermo largo 1280 pixel
    Quando l'utente apre la pagina del flusso
    Allora l'impaginazione su più colonne resta

  Scenario: Avviso della rete senza parole ripetute
    Dato che il flusso "prova-btc" è su un conto della rete di test "testnet"
    Quando l'utente apre la pagina del flusso "prova-btc"
    Allora l'avviso della rete nomina "testnet" tra virgolette senza ripetere la parola

  Scenario: Elenco dei flussi senza legenda degli esiti
    Dato uno schermo largo 360 pixel
    Quando l'utente apre l'elenco dei suoi flussi
    Allora l'elenco non ha la legenda degli esiti dei cicli recenti
