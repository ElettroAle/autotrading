# ADR esposizione-degli-altri-flussi-nel-contesto-dell-agente — Esposizione degli altri flussi del conto nel contesto dell'agente

- Stato: accettata (26 novembre 2026)
- Requisiti: US 765 R5.5.5 (Task 768)
- Collegate: ADR controllo-dell-esposizione-del-conto-nel-rischio; `.claude/rules/context-flows.md`,
  `.claude/rules/context-agent.md`, `.claude/rules/tech-fastapi.md`, `.claude/rules/tech-mcp.md`
- Verifica: prova

## Contesto e problema

R5.5.5 chiede un'opzione del flusso, spenta di default: con l'opzione accesa lo stato inviato all'agente riporta
l'esposizione long e short degli altri flussi del conto, escluso il flusso stesso.

## Fattori decisionali

- Ordine del proprietario per F5.5: opzione spenta di default, nessuna versione nuova dei flussi esistenti.
- La somma per direzione esiste già nel domain (ADR controllo-dell-esposizione-del-conto-nel-rischio): si riusa.

## Decisione

- L'opzione è una parte della configurazione versionata del flusso, spenta di default: voce `FlowSetting`, confronto
  delle versioni, creazione e modifica, documento di strategia, API e strumenti MCP con lo stesso tipo di richiesta.
- Con l'opzione accesa lo stato inviato all'agente aggiunge la riga «altri flussi del conto: long <importo> <valuta>,
  short <importo> <valuta>» dalla somma del domain con il flusso escluso; spenta, lo stato è identico a oggi.

## Alternative scartate

- **Dato sempre presente**: il proprietario lo vuole su richiesta.

## Conseguenze

- Nessun costo per i flussi con l'opzione spenta.
