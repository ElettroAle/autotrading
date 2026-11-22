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
    Quando "anna" registra un conto scegliendo l'exchange "simulato" con saldo virtuale 1000 USDC
    Allora il conto è registrato senza credenziali, sulla rete "simulato", con saldo 1000 USDC

  Scenario: Azzeramento del saldo
    Dato che "anna" ha registrato un conto "simulato" con saldo virtuale 1000 USDC
    E che il saldo virtuale del conto è 12 USDC
    Quando "anna" azzera il conto simulato con saldo 1000 USDC
    Allora il conto ha saldo 1000 USDC e nessuna posizione aperta

  Scenario: Conti simulati isolati per tenant
    Dato che "bruno" ha un conto simulato con una posizione aperta
    Quando "anna" guarda le sue posizioni
    Allora la posizione di "bruno" non compare
