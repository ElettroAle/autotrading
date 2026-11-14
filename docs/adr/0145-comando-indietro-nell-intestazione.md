# ADR 0145 — Comando «Indietro» nell'intestazione delle pagine interne

- Stato: accettata (14 novembre 2026), approvata dal proprietario
- Requisiti: Bug 260 (Task 263)
- Collegate: ADR 0116 (dashboard bulletproof-react), ADR 0117 (percorso `/dashboard`), R2.1.2 (uso da telefono)

## Contesto e problema

Da telefono non c'è modo di tornare indietro dentro la dashboard: l'intestazione mostra solo il nome e il badge
dell'ambiente, nessuno dei due è un collegamento. Serve il comando più semplice, senza introdurre un menu.

## Decisione

- Nell'intestazione condivisa (`src/components/layouts`), «AutoTrading» diventa un collegamento alla pagina principale.
- Nelle pagine diverse dalla principale compare un pulsante «Indietro» (icona e testo, area di tocco ≥ 44 px) che torna
  alla pagina precedente della cronologia del router; se la dashboard è stata aperta direttamente su quella pagina
  (nessuna pagina precedente della dashboard), porta alla pagina principale.
- Nessun menu di navigazione nuovo.

## Alternative scartate

- **Menu di navigazione completo**: più potente, ma oltre ciò che serve e più ingombrante da telefono.
- **Solo il collegamento sul nome**: semplice, ma da una pagina di dettaglio riporta sempre all'inizio invece che alla
  pagina da cui si veniva.

## Conseguenze

- Un solo componente condiviso nell'intestazione, valido per tutte le pagine presenti e future.
