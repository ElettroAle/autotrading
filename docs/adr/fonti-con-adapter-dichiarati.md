# ADR fonti-con-adapter-dichiarati — Fonti con uno o più adapter dichiarati dagli adapter stessi

- Stato: proposta (19 novembre 2026)
- Requisiti: US 310 R4.1.1, Task 311
- Collegate: ADR 0028 (catalogo delle fonti), ADR 0033 (sentiment: sostituita solo per la divisione in due fonti),
  ADR 0048, ADR 0049, ADR 0105, ADR 0140, ADR 0158, ADR peso-delle-fonti-nel-system-prompt;
  `.claude/rules/context-sources.md`, `.claude/rules/context-flows.md`, `.claude/rules/context-agent.md`
- Verifica: prova

## Contesto e problema

Oggi una fonte è un nome del catalogo del domain (`SOURCE_CATALOG`: indicatori, pivot, forecast,
`sentiment-alternative-me`, `sentiment-coinmarketcap`, notizie) con parametri interi; il flusso sceglie fonti con un
peso. R4.1.1 vuole che ogni fonte offra uno o più adapter, ciascuno dichiarato con nome, descrizione, parametri,
campi di configurazione (o «nessuna configurazione necessaria») e disponibilità dello storico, e che il flusso scelga
per ogni fonte uno o più adapter, ciascuno col suo peso e i suoi parametri. I due sentiment diventano due adapter
della fonte «sentiment».

## Fattori decisionali

- Decisione del proprietario del 15/11/2026 (backlog E4): fonti ad adapter come exchange e fornitori IA (R2.3.8,
  R2.3.9); i due sentiment diventano adapter della stessa fonte, superando la divisione di ADR 0033.
- Domain e application non nominano tecnologie o fornitori (CLAUDE.md, test di architettura): i nomi degli adapter
  («alternative.me», «CoinMarketCap», «RSS») non possono stare nel catalogo del domain.
- Precedente: l'exchange dichiara i suoi campi con `ExchangePort.credential_fields()` (ADR 0158).
- `bootstrap.py` non ha costanti né decisioni.

## Decisione

- **Domain `sources`**: la fonte resta nel catalogo del domain (`SourceDefinition`: nome, descrizione, `per_asset`, i
  parametri della fonte e la regola di silenzio). I due sentiment diventano la sola fonte `sentiment`. Nuovo value
  object `SourceAdapterDeclaration(name, description, parameters, configuration_fields, offers_history)`, con
  `SourceConfigurationField(name, label, secret)` del contesto `sources`; tupla vuota = nessuna configurazione
  necessaria. I parametri ammessi per un adapter sono quelli della fonte (regole del domain, come la scelta delle
  notizie di ADR 0034) più quelli propri dell'adapter (nessuno oggi); restano interi con minimo e massimo.
- **Dichiarazione dall'adapter**: ogni porta di lettura di una fonte (`SentimentPort`, `NewsPort`, `MarketDataPort`
  per indicatori e pivot, `PriceForecasterPort` per il forecast) aggiunge `declaration() ->
  SourceAdapterDeclaration`, statica e senza rete. Oggi: alternative.me e CoinMarketCap per `sentiment`, RSS per
  `notizie`, i dati di mercato dell'exchange per indicatori e pivot, il forecaster per `forecast`; ciascuno dichiara
  `offers_history` secondo ciò che il suo endpoint offre davvero (usato dal replay, R4.2.2).
- **Catalogo composto in application**: `SourceCatalog` diventa la combinazione delle fonti del domain con gli
  adapter collegati, costruita da un caso d'uso `ListSourcesUseCase` che riceve le porte; l'adapter è identificato
  dal nome della sua dichiarazione. `bootstrap.py` passa le porte come oggi (le sentiment in una tupla, non più in
  un dizionario con i nomi), senza nomi né costanti. API e worker compongono gli stessi adapter: le dichiarazioni
  non richiedono segreti.
- **Flusso (`flows`)**: `SourceSelection(name, adapters: tuple[AdapterSelection, ...])`, con `AdapterSelection(name,
  weight, parameters)`; il peso da 1 a 10 passa all'adapter. Una fonte selezionata senza adapter è rifiutata con
  «scegli almeno un adapter della fonte <fonte>»; adapter ripetuti nella stessa fonte rifiutati; un parametro fuori
  dai valori ammessi rifiutato con il motivo che nomina parametro e valori, come oggi.
- **Ciclo**: un nodo `source` per ogni coppia fonte-adapter attiva (ADR 0105); lettori registrati per (fonte,
  adapter). Una coppia che fallisce è assente col suo motivo (R1.2.5), le altre adapter della stessa fonte restano.
  `SourceData`, `AbsentSource` e i campioni (`SourceSample`, colonna `adapter` in `source_samples`) portano
  l'adapter; nel contesto dell'agente ogni dato ha `fonte`, `adapter` e `peso`; il segnaposto `{source_weights}` e il
  diario del ciclo nominano «fonte · adapter» con il suo peso.
- **API**: `GET /sources` elenca le fonti con i loro adapter (`adapters: [{name, description, parameters,
  configuration_fields, offers_history}]`); le richieste e risposte del flusso usano il nuovo modello.
- **Strategia esportata (ADR 0140)**: nuova `format_version`; l'importazione di un documento della versione
  precedente lo converte con la stessa corrispondenza della migrazione (ADR migrazione-delle-fonti-al-modello-ad-adapter).
- **Regole**: `.claude/rules/context-sources.md` aggiorna glossario e regola del sentiment (una fonte, due adapter),
  citando questo ADR e la decisione del proprietario.

## Alternative scartate

- Catalogo degli adapter nel domain con i nomi dei fornitori: viola il divieto di nominare tecnologie nel domain.
- Parametri dichiarati solo dall'adapter: le regole di scelta (età e numero delle notizie, lunghezza della serie degli
  indicatori) sono del domain e valgono per ogni adapter della fonte.
- Lasciare due fonti sentiment: contraddice la decisione del proprietario.

## Conseguenze

- Le fonti di E5 si aggiungono come adapter (nuova cartella e dichiarazione) senza toccare il catalogo delle fonti
  esistenti, salvo una fonte nuova.
- I campi di configurazione dichiarati saranno usati dalle credenziali degli adapter (R4.1.2).
