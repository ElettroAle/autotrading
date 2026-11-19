---
paths:
  - "src/autotrading/*/sources/**"
  - "tests/**/sources/**"
  - "specs/E1-flussi-autonomi/F1.3-fonti-dati/**"
  - "specs/E4-replay-e-analisi/F4.1-fonti-ad-adapter-configurabili/**"
---

# Contesto sources

Le fonti dati che l'agente riceve nel contesto.

## Glossario

- **Source**: informazione per il ciclo, con nome, descrizione e parametri, nel catalogo del domain: indicatori,
  pivot, forecast, sentiment, notizie (R1.3.1, R4.1.1).
- **Source adapter**: chi offre una fonte da un sistema esterno e si dichiara da sé
  (`SourceAdapterDeclaration`): nome, descrizione, parametri propri, campi di configurazione (nessuno = «nessuna
  configurazione necessaria») e disponibilità dello storico. Ogni fonte ha almeno un adapter; il catalogo
  (`SourceCatalog`) è composto in application da `ListSourcesUseCase` con le dichiarazioni delle porte
  (ADR fonti-con-adapter-dichiarati).
- **Per-asset source**: si interroga per ogni asset del flusso (indicatori, pivot, forecast). **Market
  source**: riguarda l'intero mercato e compare una sola volta nel contesto (sentiment, notizie).
- **Source parameter**: parametro con valore predefinito e valori ammessi, dichiarato dal catalogo.
- **Weight**: intero da 1 a 10, predefinito 5, per adapter scelto di una fonte attiva del flusso (R1.3.2,
  R4.1.1).
- **Sample**: valore raccolto, con fonte, adapter, asset se per asset, istante di riferimento del dato, istante
  di raccolta, ciclo e flusso (R1.3.8, R4.1.1).
- **Absent source**: fonte che nel ciclo non ha risposto in tempo o ha risposto con un errore (R1.2.5).

## Regole

- Ogni porta di lettura di una fonte chiede all'adapter `declaration()`, statica e senza rete; una dichiarazione
  si scrive solo in `adapters/outbound/`, e i nomi degli adapter non compaiono in domain, application o
  `bootstrap.py`. Un adapter nuovo di una fonte esistente si aggiunge con la sua cartella e la sua dichiarazione,
  passato da `bootstrap.py`, senza toccare il catalogo né chi compone il contesto (ADR fonti-con-adapter-dichiarati).
- I parametri ammessi per un adapter sono quelli della fonte più quelli propri dell'adapter.
- I calcoli (indicatori, pivot) sono regole del domain, sui prezzi dell'exchange del conto del flusso.
- Sentiment: una fonte con due adapter (decisione del proprietario del 15/11/2026, che supera la divisione in
  due fonti di ADR 0033): Crypto Fear & Greed Index di alternative.me e CMC Crypto Fear and Greed Index di
  CoinMarketCap, entrambi dagli endpoint pubblici senza chiave; un flusso può sceglierli entrambi, ciascuno col suo
  peso (ADR fonti-con-adapter-dichiarati).
- Le fonti dei flussi salvate prima degli adapter passano al nuovo modello con una sola corrispondenza,
  nell'adapter SQLAlchemy, usata dalla migrazione e dalla lettura delle versioni passate; la strategia esportata ne
  tiene una copia identica (ADR migrazione-delle-fonti-al-modello-ad-adapter).
- Notizie: feed RSS di CoinDesk, Cointelegraph e Decrypt; un feed che non risponde si salta, la fonte
  manca solo se nessun feed risponde. La scelta per età e numero è una regola del domain (ADR 0034).
- Forecast: smorzamento di Holt nel domain sullo storico dell'exchange (candele pubbliche di Hyperliquid
  all'intervallo più fine conservato per la profondità richiesta), orizzonti 15 minuti e 1 ora; ogni previsione
  si registra e riceve il prezzo effettivo allo scadere; lo storico più corto della profondità si dichiara
  (ADR 0043).
- Indicatori e pivot: dati di mercato pubblici di Hyperliquid (`MarketDataPort`), solo candele chiuse; timeframe
  breve = intervallo di ciclo, o l'intervallo di candela più fine sotto di esso; lungo = 4 ore; pivot dalla
  candela giornaliera UTC di ieri e dal mark price (ADR 0057, 0058).
- Una fonte esterna che non risponde produce un errore tipizzato della porta; il ciclo la tratta come
  assente, mai come errore del ciclo.
- I parametri non indicati assumono il predefinito del catalogo; un valore fuori dai valori ammessi rende
  la configurazione del flusso non valida.
- Raccolta: `CollectSourceUseCase` legge un adapter di una fonte attiva per ogni asset del flusso (o una volta,
  se di mercato) con il lettore registrato per fonte e adapter, e registra ogni valore con i suoi istanti (ADR 0048,
  0049, ADR fonti-con-adapter-dichiarati).

## Porte del contesto

Porta comune delle fonti, catalogo, repository dei campioni e delle previsioni, candele e dati di mercato
dall'exchange (`PriceHistoryPort`, `MarketDataPort`), registro delle previsioni (`ForecastRepositoryPort`).
