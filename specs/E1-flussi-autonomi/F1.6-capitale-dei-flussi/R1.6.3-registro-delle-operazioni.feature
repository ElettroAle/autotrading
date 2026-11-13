# language: it
@R1.6.3
Funzionalità: R1.6.3 Registro delle operazioni
  Come utente
  Voglio sommare, esportare e vedere insieme le operazioni dei miei flussi e dei miei conti
  Perché sappia da dove vengono i risultati di ogni flusso e possa conservarli fuori dalla piattaforma

  Il registro delle operazioni (R1.6.1) si consulta a pagine di 50 operazioni dalla più recente, con i filtri per
  asset e per periodo (inizio compreso, fine esclusa).
  - Ogni consultazione riporta anche i totali del filtro: numero di operazioni, PnL realizzato, commissioni e
    funding. I totali comprendono tutte le operazioni del filtro, non solo quelle della pagina.
  - Le operazioni di un flusso o di un conto si esportano in un file CSV con gli stessi filtri: il file contiene
    tutte le operazioni del filtro, dalla più vecchia alla più recente, con le colonne istante, flusso, asset,
    tipo, lato, quantità, prezzo, commissione, PnL realizzato e funding.
  - Le operazioni di un conto si consultano in due modi: solo quelle che non sono di nessun flusso, oppure tutte,
    di tutti i flussi del conto e di nessun flusso.
  Ogni operazione indica il suo flusso, oppure "nessun flusso".

  Fuori ambito: altri formati di esportazione, totali per asset.

  Contesto:
    Dato che "anna" ha il conto "test-1" con i flussi "alfa" (asset "BTC") e "beta" (asset "ETH")

  Scenario: Totali del periodo
    Dato che il flusso "alfa" ha esecuzioni con PnL realizzato 10 USDC e commissione 1 USDC su "BTC" alle 09:00, alle 10:30 e alle 11:30
    E che il flusso "alfa" ha ricevuto un funding di 2 USDC su "BTC" alle 11:00
    Quando "anna" consulta le operazioni del flusso "alfa" dalle 10:00 alle 12:00
    Allora i totali riportano 3 operazioni, PnL realizzato 20 USDC, commissioni 2 USDC e funding 2 USDC

  Scenario: I totali comprendono tutte le operazioni del filtro, non solo la pagina
    Dato che il flusso "alfa" ha 60 esecuzioni con PnL realizzato 1 USDC su "BTC", una al minuto
    Quando "anna" consulta la seconda pagina delle operazioni del flusso "alfa"
    Allora la pagina contiene 10 operazioni
    E i totali riportano 60 operazioni, PnL realizzato 60 USDC, commissioni 0 USDC e funding 0 USDC

  Scenario: Esportazione delle operazioni di un flusso
    Dato che il flusso "alfa" ha esecuzioni con PnL realizzato 10 USDC e commissione 1 USDC su "BTC" alle 09:00, alle 10:30 e alle 11:30
    E che il flusso "alfa" ha ricevuto un funding di 2 USDC su "BTC" alle 11:00
    Quando "anna" esporta le operazioni del flusso "alfa" dalle 10:00 alle 12:00
    Allora l'esportazione contiene le operazioni delle 10:30, delle 11:00 e delle 11:30, in quest'ordine, del flusso "alfa"

  Scenario: L'esportazione comprende tutte le operazioni del filtro, oltre la pagina
    Dato che il flusso "alfa" ha 60 esecuzioni con PnL realizzato 1 USDC su "BTC", una al minuto
    Quando "anna" esporta le operazioni del flusso "alfa"
    Allora l'esportazione contiene 60 operazioni, dalla più vecchia

  Scenario: Tutte le operazioni del conto
    Dato che il flusso "alfa" ha esecuzioni con PnL realizzato 0 USDC e commissione 0 USDC su "BTC" alle 10:00
    E che il flusso "beta" ha esecuzioni con PnL realizzato 0 USDC e commissione 0 USDC su "ETH" alle 10:10
    E che sul conto "test-1" ci sono acquisti fuori dalla piattaforma su "SOL" alle 10:20
    Quando "anna" consulta tutte le operazioni del conto "test-1"
    Allora vede l'operazione delle 10:20 di "nessun flusso", delle 10:10 di "beta" e delle 10:00 di "alfa", in quest'ordine

  Scenario: Solo le operazioni del conto che non sono di nessun flusso
    Dato che il flusso "alfa" ha esecuzioni con PnL realizzato 0 USDC e commissione 0 USDC su "BTC" alle 10:00
    E che sul conto "test-1" ci sono acquisti fuori dalla piattaforma su "SOL" alle 10:20
    Quando "anna" consulta le operazioni del conto "test-1" che non sono di nessun flusso
    Allora vede l'operazione delle 10:20 di "nessun flusso"

  Scenario: Esportazione di tutte le operazioni del conto
    Dato che il flusso "alfa" ha esecuzioni con PnL realizzato 0 USDC e commissione 0 USDC su "BTC" alle 10:00
    E che sul conto "test-1" ci sono acquisti fuori dalla piattaforma su "SOL" alle 10:20
    Quando "anna" esporta tutte le operazioni del conto "test-1"
    Allora l'esportazione contiene l'operazione delle 10:00 di "alfa" e delle 10:20 di "nessun flusso", in quest'ordine
