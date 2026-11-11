---
paths:
  - "src/autotrading/*/sources/**"
  - "tests/**/sources/**"
  - "specs/E1-flussi-autonomi/F1.3-fonti-dati/**"
---

# Contesto sources

Le fonti dati che l'agente riceve nel contesto.

## Glossario

- **Source**: fornitore di dati per il ciclo, con nome, descrizione e parametri. In E1: indicatori, pivot,
  forecast, due sentiment (`sentiment-alternative-me`, `sentiment-coinmarketcap`), notizie (R1.3.1).
- **Per-asset source**: si interroga per ogni asset del flusso (indicatori, pivot, forecast). **Market
  source**: riguarda l'intero mercato e compare una sola volta nel contesto (sentiment, notizie).
- **Source parameter**: parametro con valore predefinito e valori ammessi, dichiarato dal catalogo.
- **Weight**: intero da 1 a 10, predefinito 5, per fonte attiva del flusso (R1.3.2).
- **Sample**: valore raccolto, con fonte, asset se per asset, istante di riferimento del dato, istante di
  raccolta, ciclo e flusso (R1.3.8).
- **Absent source**: fonte che nel ciclo non ha risposto in tempo o ha risposto con un errore (R1.2.5).

## Regole

- Ogni fonte implementa la stessa porta e si dichiara al catalogo: una fonte nuova si aggiunge con un
  adapter registrato in `bootstrap.py`, senza toccare chi compone il contesto.
- I calcoli (indicatori, pivot) sono regole del domain, sui prezzi dell'exchange del conto del flusso.
- Sentiment: due fonti distinte (decisione del proprietario), perché sono due indici diversi con lo stesso
  nome: Crypto Fear & Greed Index di alternative.me e CMC Crypto Fear and Greed Index di CoinMarketCap, entrambi
  dagli endpoint pubblici senza chiave (ADR 0033).
- Una fonte esterna che non risponde produce un errore tipizzato della porta; il ciclo la tratta come
  assente, mai come errore del ciclo.
- I parametri non indicati assumono il predefinito del catalogo; un valore fuori dai valori ammessi rende
  la configurazione del flusso non valida.

## Porte del contesto

Porta comune delle fonti, catalogo, repository dei campioni e delle previsioni, candele e dati di mercato
dall'exchange, servizio di previsione.
