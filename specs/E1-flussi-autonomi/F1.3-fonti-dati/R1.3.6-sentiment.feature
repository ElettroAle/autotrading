# language: it
@R1.3.6 @wip
Funzionalità: R1.3.6 Fonti sentiment di mercato
  Come utente
  Voglio che l'agente riceva l'indice Fear & Greed del mercato cripto
  Perché tenga conto dell'umore generale del mercato

  Due fonti distinte, selezionabili una indipendentemente dall'altra, perché sono due indici diversi con lo
  stesso nome e metodologie proprie:
  - "sentiment-alternative-me": il Crypto Fear & Greed Index di alternative.me, senza chiave;
  - "sentiment-coinmarketcap": il CMC Crypto Fear and Greed Index di CoinMarketCap, con una chiave API della piattaforma
    (non dell'utente).
  A ogni ciclo ogni fonte attiva rileva il proprio indice corrente: valore da 0 a 100, classificazione testuale
  e istante di aggiornamento dell'indice. L'indice riguarda l'intero mercato cripto: compare una sola volta nel
  contesto, non per asset.

  Fuori ambito: sentiment per singolo asset, sentiment dai social.

  Schema dello scenario: Indice nel contesto
    Dato che "anna" ha il flusso "alfa" con asset "BTC, ETH" e la fonte "<fonte>" attiva
    E che l'indice Fear & Greed di "<fonte>" vale 72 con classificazione "Greed"
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene una sola volta l'indice Fear & Greed di "<fonte>" con valore 72 e classificazione "Greed"
    E il contesto riporta l'istante di aggiornamento dell'indice di "<fonte>"

    Esempi:
      | fonte                   |
      | sentiment-alternative-me |
      | sentiment-coinmarketcap |

  Scenario: Entrambe le fonti attive
    Dato che "anna" ha il flusso "alfa" con le fonti "sentiment-alternative-me, sentiment-coinmarketcap" attive
    E che l'indice Fear & Greed di "sentiment-alternative-me" vale 72 con classificazione "Greed"
    E che l'indice Fear & Greed di "sentiment-coinmarketcap" vale 55 con classificazione "Neutral"
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene l'indice di "sentiment-alternative-me" con valore 72 e quello di "sentiment-coinmarketcap" con valore 55, ciascuno con la propria fonte
