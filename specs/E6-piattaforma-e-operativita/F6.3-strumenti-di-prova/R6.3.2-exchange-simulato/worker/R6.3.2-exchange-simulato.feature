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

  Contesto:
    Dato che "anna" ha registrato un conto "simulato" con saldo virtuale 1000 USDC

  Scenario: Ordine eseguito al prezzo reale
    Dato che il prezzo reale di BTC è 90000 USDC
    Quando il flusso "alfa" apre un long BTC da 100 USDC a leva 2
    Allora la posizione è aperta vicino a 90000 USDC con slippage e commissione applicati
    E il saldo virtuale scende della commissione

  Scenario: Regole del mercato
    Quando il flusso "alfa" invia un ordine sotto l'importo minimo del mercato
    Allora l'ordine è rifiutato con lo stesso errore dell'exchange vero

  Scenario: Stop loss sul prezzo reale
    Dato che il flusso "alfa" ha un long BTC con stop loss a 88000 USDC
    Quando il prezzo reale di BTC scende a 88000 USDC
    Allora la posizione si chiude allo stop loss e la perdita entra nel saldo virtuale

  Scenario: Liquidazione
    Dato che il flusso "alfa" ha un long BTC a leva 10
    Quando il prezzo reale scende oltre il prezzo di liquidazione
    Allora la posizione risulta liquidata

  Scenario: Stato conservato
    Dato che il flusso "alfa" ha un long BTC aperto sul conto simulato
    Quando la piattaforma si riavvia
    Allora la posizione è ancora aperta con lo stesso prezzo di ingresso
