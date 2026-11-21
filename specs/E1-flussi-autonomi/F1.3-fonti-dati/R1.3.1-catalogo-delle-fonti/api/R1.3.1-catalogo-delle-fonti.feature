# language: it
@R1.3.1
Funzionalità: R1.3.1 Catalogo delle fonti dati
  Come utente
  Voglio consultare le fonti dati disponibili con i loro parametri
  Perché sappia che cosa posso attivare in un flusso e con quali valori

  Il catalogo elenca per ogni fonte: nome, descrizione, parametri con valore predefinito e valori ammessi.
  In E1 le fonti sono: indicatori, pivot, forecast, due fonti sentiment (alternative.me e CoinMarketCap),
  notizie.
  Una fonte aggiunta alla piattaforma compare nel catalogo e diventa selezionabile nei flussi senza altre
  modifiche; una fonte ritirata scompare dal catalogo.

  Fuori ambito: le fonti whale e volumi globali, previste in un'epica successiva.

  Scenario: Fonti disponibili
    Quando "anna" consulta il catalogo delle fonti
    Allora il catalogo contiene le fonti:
      | fonte                   |
      | indicatori              |
      | pivot                   |
      | forecast                |
      | sentiment-alternative-me |
      | sentiment-coinmarketcap |
      | notizie                 |

  Scenario: Parametri di una fonte
    Quando "anna" consulta la fonte "notizie" nel catalogo
    Allora la fonte "notizie" ha i parametri:
      | parametro       | predefinito | ammessi       |
      | numero notizie  | 10          | da 1 a 50     |
      | età massima ore | 24          | da 1 a 168    |

  Scenario: Una fonte aggiunta compare nel catalogo ed è selezionabile
    Dato che la piattaforma aggiunge la fonte "volumi" con l'adapter "Binance"
    Quando "anna" consulta il catalogo delle fonti
    Allora il catalogo contiene la fonte "volumi" con l'adapter "Binance"
    E "anna" può creare un flusso con la fonte "volumi"

  Scenario: Una fonte ritirata scompare dal catalogo
    Dato che la piattaforma ritira la fonte "sentiment"
    Quando "anna" consulta il catalogo delle fonti
    Allora il catalogo non contiene la fonte "sentiment"
    E la creazione di un flusso di "anna" con la fonte "sentiment" è rifiutata con il motivo "fonte non disponibile: sentiment"
