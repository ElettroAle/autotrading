# ADR limite-di-perdite-consecutive-del-flusso — Limite di perdite consecutive nella configurazione del flusso

- Stato: accettata (26 novembre 2026)
- Requisiti: US 754 R5.5.2 (Task 755)
- Collegate: ADR perdita-giornaliera-dalla-ripresa-delle-aperture (perdita massima, stessa famiglia), ADR 0051;
  `.claude/rules/context-flows.md`, `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-fastapi.md`,
  `.claude/rules/tech-mcp.md`
- Verifica: prova

## Contesto e problema

R5.5.2 chiede un limite di rischio facoltativo: perdite consecutive massime (intero ≥ 1), finestra delle perdite (ore,
≥ 1), durata del blocco (minuti, ≥ 1), tutte e tre insieme o nessuna, e l'ambito del conteggio («asset» o «flusso»,
«asset» se non indicato, ammesso solo con le altre tre).

## Fattori decisionali

- Requisito R5.5.2 e i suoi motivi di rifiuto letterali.
- Ordine del proprietario per F5.5 (26 novembre 2026): impostazioni facoltative, vuote di default; i flussi esistenti
  non ricevono una versione nuova.
- Le soglie di perdita massima sono parti facoltative della configurazione versionata (R3.2.2): stessa famiglia.

## Decisione

- **Domain.** Un value object `ConsecutiveLossLimit` (perdite consecutive massime, finestra, durata, ambito
  `LossCountScope`: asset, flusso) facoltativo nella `FlowConfiguration`, accanto alle soglie della perdita massima.
  Le invarianti sono del domain, con errori tipizzati e i motivi dei criteri: «perdite consecutive massime, finestra
  delle perdite e durata del blocco si impostano insieme», «le perdite consecutive massime sono almeno 1», «la finestra
  delle perdite è di almeno 1 ora», «la durata del blocco è di almeno 1 minuto», «l'ambito del conteggio è asset oppure
  flusso». Un ambito senza le tre parti è rifiutato con il primo motivo; senza ambito vale «asset».
- **Configurazione versionata.** Le parti si salvano con la versione; voci `FlowSetting`, righe del confronto delle
  versioni, creazione, modifica, rimozione del limite intero (un solo flag `remove_*`), documento di strategia, API e
  strumenti MCP con lo stesso tipo di richiesta condiviso.
- **Nessuna migrazione dei dati.** Nel documento salvato della configurazione le parti sono facoltative e, mancanti,
  si leggono vuote (come lo stop che segue il prezzo, ADR impostazioni-dello-stop-che-segue-il-prezzo): le versioni
  esistenti non hanno il limite e non cambiano versione.

## Alternative scartate

- **Tre impostazioni indipendenti**: il requisito le vuole insieme; separate darebbero limiti incompleti.

## Conseguenze

- Un flusso senza il limite resta identico.
