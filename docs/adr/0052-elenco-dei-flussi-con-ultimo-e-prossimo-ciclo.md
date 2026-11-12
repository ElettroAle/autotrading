# ADR 0052 — Elenco dei flussi con ultimo e prossimo ciclo

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.7.3 (scenario "Elenco dei flussi")
- Collegate: ADR 0042 (integrazione dei cicli nel worker), 0046 (registrazione dei cicli)

## Contesto

R1.7.3 chiede l'elenco dei flussi in uso, ciascuno con nome, conto, ambiente, stato, motivo dell'eventuale pausa
automatica, modello, ultimo ciclo con il suo esito e prossimo ciclo previsto. L'ancora dei cicli (ultimo avvio o
ripresa) e il motivo della pausa automatica stanno sulla riga del flusso dal lavoro di ADR 0042, ma l'entità
`Flow` non li porta; i cicli registrati stanno nel contesto `cycles` (ADR 0046).

## Decisione

- **Porta `FlowTimingPort`** nel contesto `flows`, legata al tenant: per ogni flusso l'ancora e il motivo della
  pausa (`FlowTiming`). Adapter `SqlAlchemyFlowTimingAdapter` sulle colonne `cycle_anchor` e `pause_reason`.
  L'entità `Flow` resta com'è: ancora e motivo li scrivono il database e la pausa automatica, non i casi d'uso del
  flusso.
- **Caso d'uso `ListFlowOverviewsUseCase`** nel contesto `cycles`, sulla porta `FlowSummaryPort` (i flussi in uso
  già riassunti) e su `CycleHistoryPort` (l'ultimo ciclo). Il prossimo ciclo è il primo istante pianificato dopo
  adesso, solo per un flusso attivo; un flusso in pausa o fermo non ne ha.
- **Ponte `FlowSummariesFromFlows`** in `bootstrap.py`: flussi in uso, nome del conto e tempi del flusso.
- **API**: `GET /flows/overview`, accanto ai cicli. `GET /flows` resta la lista delle configurazioni in vigore.
- L'ambiente è quello dell'installazione dell'API.

## Alternative scartate

- **Ancora e motivo dentro `Flow`**: ogni caso d'uso del flusso dovrebbe portarli senza mai cambiarli.
- **Campi aggiunti a `GET /flows`**: mescola la configurazione con lo stato di esecuzione, e la lista degli
  archiviati non ha cicli da mostrare.

## Conseguenze

- Una consultazione legge i flussi, i conti e l'ultimo ciclo di ogni flusso: una query per flusso, accettabile con
  pochi flussi per utente.
