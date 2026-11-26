# ADR costo-di-andata-e-ritorno-nel-contesto-dell-agente — Commissioni di andata e ritorno nel contesto dell'agente

- Stato: accettata (26 novembre 2026)
- Requisiti: US 770 R5.5.6 (Task 771)
- Collegate: ADR 0007, ADR 0089 (un adapter una tecnologia); `.claude/rules/context-flows.md`,
  `.claude/rules/context-agent.md`, `.claude/rules/tech-hyperliquid.md`, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.5.6 chiede un'opzione del flusso, spenta di default: accesa, lo stato inviato all'agente riporta il costo di andata e
ritorno in percentuale del valore della posizione, cioè la commissione che l'exchange applica al conto per un ordine a
mercato contata per l'apertura e per la chiusura. Se l'exchange non la dà, il costo va tra i dati mancanti e il ciclo
non fallisce.

## Fattori decisionali

- Ordine del proprietario per F5.5: opzione spenta di default, nessuna versione nuova dei flussi esistenti.
- Niente ponti tra contesti: `flows` dichiara la porta con cui legge la commissione del conto; l'adapter dell'exchange
  (e quello simulato) la realizza nella sua cartella. Le credenziali le usa solo il worker (ADR 0007).
- Nessun codice per un fornitore nel domain e nell'application.

## Decisione

- **Opzione.** Parte della configurazione versionata del flusso, spenta di default: voce `FlowSetting`, confronto delle
  versioni, creazione e modifica, documento di strategia, API, strumenti MCP e casella nel modulo del flusso accanto
  alle altre opzioni del contesto dell'agente, con la riga di aiuto.
- **Lettura.** Una porta del contesto `flows` restituisce la commissione per un ordine a mercato (taker) del conto del
  flusso; l'adapter Hyperliquid la legge dall'exchange, l'exchange simulato dalla sua configurazione. Si legge solo con
  l'opzione accesa, una volta per ciclo.
- **Regola nel domain.** Il costo di andata e ritorno è la commissione per due (apertura e chiusura), in percentuale; lo
  stato inviato all'agente aggiunge la riga con quel valore. Una lettura che fallisce con un errore temporaneo o
  permanente dell'exchange diventa il dato mancante «costo di andata e ritorno»; il ciclo continua.

## Alternative scartate

- **Commissione fissa nella configurazione**: il requisito vuole quella che l'exchange applica al conto.

## Conseguenze

- Una lettura in più per ciclo, solo con l'opzione accesa.
