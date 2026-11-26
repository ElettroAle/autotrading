# ADR memoria-del-flusso-con-riepilogo-e-altri-asset — Memoria del flusso: riepilogo per asset e direzione e vista tra asset

- Stato: accettata (26 novembre 2026)
- Requisiti: US 762 R5.3.7 (Task 763)
- Collegate: ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni (estesa, non sostituita), ADR
  system-prompt-del-flusso-come-modello-con-segnaposti, ADR chiusure-per-protezione-nello-storico;
  `.claude/rules/context-flows.md`, `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-fastapi.md`,
  `.claude/rules/tech-mcp.md`
- Verifica: prova

## Contesto e problema

R5.3.7 chiede due opzioni della memoria, spente di default e valide con la memoria attiva: il riepilogo (una riga per
direzione con posizioni chiuse sull'asset nei giorni della memoria, in testa alla memoria dell'asset) e gli altri asset
(le righe di riepilogo degli altri asset del flusso, dopo il riepilogo, senza le loro decisioni).

## Fattori decisionali

- Requisito R5.3.7: la riga conta le posizioni chiuse, non le decisioni, e non dipende dal numero di decisioni; forma
  letterale della riga; oggi è il giorno UTC; vinta = PnL netto sopra zero, persa = sotto zero, in pari conta solo tra
  le chiuse; la memoria letta dall'utente mostra le righe come le riceve l'agente.
- Ordine del proprietario per F5.5 e R5.3.7: opzioni spente di default, i flussi esistenti non cambiano versione.
- Il risultato netto è del domain (`ClosedPosition.net_pnl`).
- Ambiguità risolta: la memoria scrive oggi i numeri col punto decimale (scelta di R5.3.5), mentre i criteri di R5.3.7
  scrivono la riga con la virgola («PnL -6,27 USDC»). Si segue il criterio: la riga di riepilogo scrive gli importi
  con il formato italiano del domain (`number_text`), le altre parti della memoria restano come sono.

## Decisione

Resta tutto ciò che decide l'ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni; si aggiunge:

- **Opzioni.** `FlowMemory` ha `summary` e `other_assets`, spente di default, parte della versione come le altre parti
  della memoria; API, strumenti MCP, documento di strategia, differenze tra versioni e modulo con lo stesso tipo di
  richiesta di memoria condiviso. Nessuna migrazione dei dati: nel documento salvato le due opzioni sono facoltative e,
  mancanti, si leggono spente; le versioni esistenti non cambiano.
- **Righe nel domain.** Un tipo del domain calcola, dalle posizioni chiuse del flusso nei giorni della memoria, per ogni
  asset e direzione: chiuse, vinte, perse e PnL netto di oggi (giorno UTC dell'istante del ciclo) e dei giorni della
  memoria; una direzione senza chiuse non ha riga. Forma: «<asset> <direzione> — oggi: <n> chiuse, <n> vinte, <n>
  perse, PnL <importo> <valuta>; ultimi <giorni> giorni: …».
- **Composizione.** `AssetMemory` porta le righe di riepilogo dell'asset (con `summary`) e quelle degli altri asset
  (con `other_assets`), poi le decisioni come oggi. Il testo del segnaposto della memoria e la lettura della memoria
  (dashboard, API, MCP) usano la stessa composizione.
- **Lettura.** Una porta del contesto `flows` restituisce le posizioni chiuse del flusso nei giorni della memoria
  (adapter `sqlalchemy/` sotto RLS), letta solo con una delle due opzioni accese.

## Alternative scartate

- **Riepilogo dalle decisioni della memoria**: il requisito conta le posizioni chiuse, senza il limite delle decisioni.

## Conseguenze

- Una lettura in più dello storico delle posizioni chiuse per ciclo, solo con le opzioni accese.
