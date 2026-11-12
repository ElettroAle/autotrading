# ADR 0034 — Notizie dai feed RSS di tre testate, selezione nel domain

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.3.7 (Task T1.3.7.1)

## Contesto

R1.3.7 porta nel ciclo le notizie cripto più recenti, ciascuna con titolo, data e ora di pubblicazione e
sintesi, dalla più recente, con due parametri per flusso: numero di notizie (1-50, predefinito 10) ed età
massima in ore (1-168, predefinita 24). L'architettura indica i feed RSS; il requisito non nomina le testate.
Le fonti esterne sono instabili (rischio T8 di `docs/architecture.md`): una testata che non risponde non deve
togliere le notizie delle altre.

Una prova diretta mostra tre testate generaliste con feed RSS 2.0 pubblici, senza chiave e con decine di
notizie ciascuno: CoinDesk (25), Cointelegraph (30), Decrypt (37). Bitcoin Magazine rifiuta i client
automatici (403); The Block risponde ma pubblica meno notizie.

Il ciclo (F1.2) che compone il contesto non esiste ancora: gli scenari di R1.3.7 restano `@wip` finché non
arriva.

## Decisione

- **Domain**: `NewsItem` (titolo non vuoto, istante di pubblicazione con fuso, sintesi) e la regola
  `recent_news(items, count, max_age, now)`: tiene le notizie non più vecchie dell'età massima (il limite è
  incluso), dalla più recente, al massimo `count`. Nessuna notizia recente dà una tupla vuota: il contesto la
  dichiara (scenario "Nessuna notizia recente").
- **Porta** `NewsPort.read_latest()` in `application/sources/ports.py`.
- **Adapter** `HttpxRssNewsAdapter` in `adapters/outbound/httpx/news.py`, sui feed di CoinDesk, Cointelegraph e
  Decrypt, con la libreria standard per l'XML e l'HTML: nessuna dipendenza nuova.
  - Un feed che non risponde, risponde con uno stato di errore o con qualcosa che non è RSS si salta; una
    notizia senza titolo o senza data con fuso si salta. Se nessun feed risponde, `SourceUnavailableError`
    "fonte non raggiungibile: notizie" (503, transitorio).
  - La sintesi è il testo della descrizione senza markup, con gli spazi compattati, tagliata a 500 caratteri
    con un'ellissi: fino a 50 notizie entrano in ogni ciclo, e la sintesi limita il contesto dell'agente.
  - L'XML si legge con `xml.etree`: expat non risolve entità esterne e limita l'espansione delle entità.
- **Prova dal vivo** con il marcatore `sources` (ADR 0033), un caso per testata.

## Alternative scartate

- **feedparser**: legge anche Atom e formati irregolari, ma aggiunge una dipendenza per tre feed RSS 2.0
  regolari, e scarica da sé gli URL, fuori dal client httpx con il suo timeout.
- **API di notizie a chiave (CryptoPanic, CryptoCompare)**: un segreto da gestire e un piano a pagamento per
  volumi che i feed RSS coprono.
- **Selezione nell'adapter**: età e numero sono parametri del flusso e regole del requisito, non della
  tecnologia; nel domain si provano senza rete.
- **Deduplica tra testate**: la stessa notizia ha titoli diversi su testate diverse; un confronto esatto non la
  riconosce e uno approssimato è una regola che il requisito non chiede.

## Conseguenze

- Le testate si cambiano in `NEWS_FEEDS`: la prova dal vivo rivela un feed ritirato o bloccato.
- Le notizie sono in inglese: l'agente le riceve come pubblicate.
- Il collegamento al ciclo arriva con F1.2.
