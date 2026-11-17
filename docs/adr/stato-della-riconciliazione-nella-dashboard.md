# ADR stato-della-riconciliazione-nella-dashboard — Stato della riconciliazione nella dashboard

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.3.2 (463), Task T3.3.2.1 (486)
- Collegate: ADR allarme-di-riconciliazione-sul-saldo-del-conto, ADR tabella-condivisa-senza-sforamento-e-con-filtri,
  ADR pagina-del-flusso-a-schede-sotto-un-periodo-comune

## Contesto e problema

R3.3.1 espone nell'API l'ultimo confronto, la soglia, gli allarmi e la conferma di un conto; la pagina Conti
(`features/accounts`) mostra solo stato e azioni del conto e la pagina del flusso non sa se le aperture sono sospese.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile
  (`ConfirmationDialog`, `DataTable`, `details-list`, campi di `components/ui/form`), nessun duplicato per pagina.
- `.claude/rules/tech-dashboard.md`: nessuna logica di business nella dashboard (stato, scostamento e motivo della
  sospensione li dà l'API), client generato dall'OpenAPI, nessun import tra funzionalità.
- R3.3.2: stato "allineato"/"allarme" con ultimo confronto, atteso, letto, scostamento e soglia; "Ho verificato" con
  conferma; elenco degli allarmi dal più recente; soglia modificabile; avviso sul flusso.

## Opzioni considerate

1. Nella funzionalità `accounts`: un componente `ReconciliationStatus` per ogni conto della pagina Conti (lista
   etichetta-valore di `details-list`), il comando "Ho verificato" con `ConfirmationDialog`, il form della soglia con
   i campi di `components/ui/form`; una rotta `/accounts/:accountId/alarms` con l'elenco degli allarmi su
   `DataTable`. Lo stato del flusso nell'API porta la sospensione delle aperture (`openings_suspension`, un solo
   campo per ogni causa, ADR perdita-massima-nella-dashboard), che la pagina del flusso mostra con il componente
   condiviso dell'avviso: "aperture sospese: allarme di riconciliazione sul conto test-1", senza il comando di
   ripresa.
2. Una pagina separata della riconciliazione per tutti i conti: scartata, lo stato serve accanto al conto e ai suoi
   comandi.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari Playwright di R3.3.2, unit test dei componenti, test dell'API dello stato del flusso).

### Conseguenze

- L'utente vede e sblocca un allarme senza usare l'interfaccia programmatica.
