# ADR 0048 — Raccolta delle fonti attive di un flusso, con pesi e parametri

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.3.2 (Task T1.3.2.1)

## Contesto

R1.3.2 chiede che ogni flusso scelga quali fonti attivare, con un peso intero da 1 a 10 (predefinito 5) e i
parametri del catalogo (R1.3.1), con i valori predefiniti per quelli non indicati. Una fonte attiva si interroga
per ogni asset del flusso; una fonte non attiva non si interroga e non compare nel contesto dell'agente.

La configurazione del flusso già valida pesi e parametri alla creazione (`SourceSelection`,
`SourceDefinition.settings`, ADR 0031). Il nucleo del ciclo (ADR 0041) chiede a una `SourcePort` i dati di ogni
fonte attiva, in parallelo, ma nessuna fonte del catalogo sa ancora rispondere: le prove di R1.3.3-R1.3.7 coprono
i calcoli e gli adapter, non la lettura dentro un ciclo. Il contesto dell'agente porta già un peso per ogni dato
(`SourceData`, ADR 0038).

## Decisione

- **Caso d'uso** `CollectSourceUseCase` nel contesto `sources`: riceve una fonte attiva come la configurazione la
  seleziona (nome, peso, parametri), gli asset del flusso, il ciclo e l'istante di raccolta.
  - Risolve la fonte nel catalogo e applica di nuovo `settings`: i parametri non indicati prendono il valore
    predefinito, uno fuori dai valori ammessi è rifiutato prima di qualsiasi lettura.
  - Una fonte per asset si legge una volta per asset, nell'ordine del flusso; una fonte di mercato una volta sola.
  - Restituisce `CollectedSource` (fonte, peso, valori raccolti) e registra i valori (ADR 0049).
- **Porta** `SourceReaderPort.execute(ReadSourceCommand)`: un lettore per fonte del catalogo, scelto per nome.
  Una fonte del catalogo senza lettore è "fonte non disponibile", come una fuori dal catalogo.
- **Lettori** come casi d'uso del contesto `sources`, sulle porte che esistono già:
  `ReadSentimentUseCase` (R1.3.6), `ReadNewsUseCase` (R1.3.7, con `recent_news` e i parametri del flusso),
  `ReadForecastUseCase` (R1.3.5, su `ForecastAssetUseCase`). I lettori di indicatori e pivot arrivano con
  l'integrazione dei cicli, insieme ai dati di mercato che servono loro.
- **Ponte** `agent_sources_of` in `bootstrap.py`: ogni valore raccolto diventa un `SourceData` del contesto con il
  peso della sua fonte. Il contesto contiene solo ciò che le fonti attive hanno raccolto.
- **Scenari** di R1.3.2 sul caso d'uso, con lettori finti, e sul contesto composto dal ponte. Lo schema "Peso o
  parametro non valido" parla di una modifica del flusso e resta `@wip` fino a R1.1.3.

## Alternative scartate

- **Lettura dentro l'adapter della `SourcePort` del ciclo**: la regola "per asset o una volta sola" e i valori
  predefiniti sono regole del requisito, non della tecnologia; nel caso d'uso si provano senza rete.
- **Un caso d'uso per tutte le fonti del flusso**: il ciclo già interroga le fonti in parallelo, ciascuna con la
  propria attesa (ADR 0041); un caso d'uso per fonte resta dentro quel modello.
- **Peso applicato ai valori (media pesata)**: il requisito chiede di comunicare il peso all'agente, non di
  trasformare i dati.

## Conseguenze

- L'integrazione dei cicli collega `SourcePort` a `CollectSourceUseCase`, leggendo selezione e asset dalla
  versione della configurazione del flusso.
- Una lettura che fallisce per un asset rende assente l'intera fonte nel ciclo, e non registra nulla.
- Le notizie arrivano all'agente una per una, ciascuna con il peso della fonte.
