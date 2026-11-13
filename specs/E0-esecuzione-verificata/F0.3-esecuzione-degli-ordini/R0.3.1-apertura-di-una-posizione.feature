# language: it
@R0.3.1
Funzionalità: R0.3.1 Apertura di una posizione sull'exchange
  Come piattaforma
  Voglio aprire una posizione long o short con leva e dimensione indicate
  Perché la procedura di verifica, e in seguito i flussi, possano operare sul conto

  L'apertura non è un comando dell'utente: la usano la procedura di verifica e, in seguito, i flussi.
  Ogni ordine porta un identificativo assegnato dalla piattaforma, che lo collega a chi lo ha generato.
  L'ordine è a mercato con uno scostamento massimo di prezzo; oltre lo scostamento non viene eseguito.
  Lo scostamento massimo è configurabile; il valore predefinito è 5%.
  Ogni posizione si apre con margine isolato: la sua perdita massima è il margine che le è assegnato, e non
  intacca la garanzia delle altre posizioni del conto, anche quando appartengono ad altri flussi.

  Fuori ambito: ordini limite in attesa, chiusure parziali, stop loss e take profit.

  Contesto:
    Dato che il conto "test-1" è su "Hyperliquid" con margine disponibile 1000 USDC e nessuna posizione aperta

  Schema dello scenario: Apertura riuscita
    Quando la piattaforma apre sul conto "test-1" una posizione "<direzione>" su "<asset>" con leva <leva> e valore 20 USDC
    Allora sull'exchange il conto "test-1" ha una posizione "<direzione>" su "<asset>"
    E la posizione su "<asset>" ha leva <leva>
    E la posizione su "<asset>" ha margine isolato
    E l'ordine inviato porta un identificativo della piattaforma

    Esempi:
      | direzione | asset | leva |
      | long      | BTC   | 2    |
      | short     | ETH   | 3    |

  Scenario: Scostamento massimo predefinito
    Dato che lo scostamento massimo di prezzo non è configurato
    Quando la piattaforma apre sul conto "test-1" una posizione "long" su "BTC" con leva 2 e valore 20 USDC
    Allora l'ordine inviato accetta uno scostamento massimo del 5% dal prezzo corrente

  Scenario: Prezzo oltre lo scostamento massimo configurato
    Dato che lo scostamento massimo di prezzo è configurato all'1%
    E che il prezzo di "BTC" si muove di più dell'1% prima dell'esecuzione
    Quando la piattaforma apre sul conto "test-1" una posizione "long" su "BTC" con leva 2 e valore 20 USDC
    Allora l'ordine non è eseguito
    E l'esito riporta il motivo "prezzo oltre lo scostamento massimo"

  Scenario: Leva oltre il massimo dell'exchange per l'asset
    Dato che l'exchange ammette per "BTC" una leva massima di 40
    Quando la piattaforma apre sul conto "test-1" una posizione "long" su "BTC" con leva 50 e valore 20 USDC
    Allora l'ordine non è inviato
    E l'esito riporta il motivo "leva oltre il massimo dell'exchange per BTC: 40"

  Scenario: Dimensione arrotondata ai passi dell'exchange
    Dato che l'exchange ammette per "BTC" dimensioni multiple di 0.00001
    Quando la piattaforma apre sul conto "test-1" una posizione "long" su "BTC" con un valore che corrisponde a 0.000234567 BTC
    Allora l'ordine inviato ha dimensione 0.00023 BTC
