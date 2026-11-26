# ADR controllo-dell-esposizione-del-conto-nel-rischio — Controllo dell'esposizione per direzione del conto nel rischio del ciclo

- Stato: accettata (26 novembre 2026)
- Requisiti: US 765 R5.5.5 (Task 767)
- Collegate: ADR esposizione-massima-per-direzione-del-conto, ADR 0040 (controllo del rischio), ADR
  capitale-libero-al-netto-del-valore-dei-flussi; `.claude/rules/context-flows.md`, `.claude/rules/context-accounts.md`
- Verifica: prova

## Contesto e problema

Con il limite del conto impostato, un'apertura di un flusso è bloccata quando l'esposizione del conto in quella
direzione più il valore dell'apertura supera il limite (percentuale del saldo letto dall'exchange). Nessuna riduzione,
nemmeno con «porta al minimo». Di un'inversione bloccata si esegue la sola chiusura.

## Fattori decisionali

- Regole di R5.5.5: esposizione per direzione = somma di dimensione × prezzo di mercato delle posizioni dei flussi non
  archiviati del conto; direzioni senza compensazione; posizioni non spiegate da un flusso escluse; esattamente al limite
  passa; motivo letterale dei criteri.
- Niente ponti tra contesti: `flows` dichiara la porta con cui legge il limite del conto; l'adapter `sqlalchemy/` la
  realizza.
- Il ciclo legge già posizioni e saldo del conto con una lettura sola (ADR
  capitale-libero-al-netto-del-valore-dei-flussi).
- L'ordine rispetto agli altri controlli è lasciato all'ADR dal Task: scelta presa qui senza una regola scritta.

## Decisione

- **Somma nel domain.** Un tipo del domain calcola l'esposizione long e short del conto dalle posizioni attribuite ai
  flussi non archiviati del conto (stessa attribuzione del capitale libero), con un flusso escluso a richiesta: serve
  al limite (nessuno escluso) e al contesto dell'agente (escluso il flusso stesso, ADR
  esposizione-degli-altri-flussi-nel-contesto-dell-agente).
- **Rischio.** `RiskCheck` riceve il limite in valuta (percentuale × saldo) e l'esposizione del conto; il controllo del
  conto viene **dopo** i controlli del flusso, e quindi dopo un'eventuale riduzione dell'apertura per i limiti del
  flusso: si controlla il valore che verrebbe davvero inviato. Oltre il limite l'apertura diventa bloccata con il motivo
  («apertura short su ETH bloccata: esposizione short del conto 1300 USDC oltre il limite di 1200 USDC (60% del saldo
  2000 USDC)»), senza riduzione. Più aperture nello stesso ciclo si sommano nell'ordine in cui il controllo le approva.
  Di un'inversione si approva la chiusura e si blocca l'apertura opposta.
- **Lettura.** Il ciclo legge il limite del conto con una porta del contesto `flows` solo se il conto ne ha uno; senza
  limite nessun calcolo in più.

## Alternative scartate

- **Controllo del conto prima dei limiti del flusso**: bloccherebbe aperture che i limiti del flusso avrebbero ridotto
  entro il limite del conto.
- **Ridurre l'apertura al residuo del conto**: escluso dal requisito.

## Conseguenze

- Il limite vale sulle posizioni lette all'inizio del ciclo; aperture di altri flussi nello stesso istante non si vedono
  a vicenda.
