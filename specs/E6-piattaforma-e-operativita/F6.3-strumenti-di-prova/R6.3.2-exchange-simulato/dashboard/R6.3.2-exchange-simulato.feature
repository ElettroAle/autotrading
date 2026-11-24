# language: it
@R6.3.2
Funzionalità: R6.3.2 Exchange simulato
  Come utente
  Voglio un exchange simulato con il mercato vero
  Perché provo i flussi all'infinito senza consumare i fondi della rete di test

  L'exchange simulato è un adapter di exchange come gli altri (R2.3.8): si sceglie alla registrazione del conto, non
  chiede credenziali e dichiara il proprio nome di rete ("simulato"), mostrato nell'avviso della rete (R2.3.10). Prezzi
  e candele sono quelli reali, letti dai dati pubblici di Hyperliquid mainnet in sola lettura. Gli ordini non arrivano a
  nessun exchange: l'adapter li esegue in simulazione con le regole del mercato (importo minimo, passo di prezzo e
  quantità, leva massima), commissioni, slippage configurabile, stop loss e take profit sui prezzi reali, liquidazione.
  Il conto ha un saldo virtuale che l'utente indica alla registrazione e può azzerare quando vuole; posizioni, ordini e
  storico del conto simulato appartengono al tenant e restano dopo un riavvio. Il resto della piattaforma (ciclo,
  rischio, viste, classifica) non distingue un conto simulato da uno vero. Lo stesso motore di esecuzione serve al
  replay (R4.2.3).

  Scenario: Registrazione senza credenziali
    Quando "anna" registra un conto scegliendo l'exchange "simulato"
    Allora il modulo non chiede credenziali ma il saldo virtuale
    E il conto mostra l'avviso della rete "simulato"

  Scenario: Azzeramento del saldo dalla pagina del conto
    Dato che "anna" ha un conto "simulato" con saldo virtuale 12 USDC
    Quando "anna" azzera il conto dalla sua pagina con saldo 1000 USDC
    Allora la pagina del conto mostra saldo 1000 USDC
