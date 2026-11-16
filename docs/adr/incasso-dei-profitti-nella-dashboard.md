# ADR incasso-dei-profitti-nella-dashboard — Incasso dei profitti tra i comandi del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.4.1 (464), Task T3.4.1.2 (488)
- Collegate: ADR incasso-dei-profitti, ADR viste-e-comandi-della-pagina-del-flusso, ADR 0116 (struttura della
  dashboard)

## Contesto e problema

La dashboard deve offrire l'incasso con una conferma che mostra il profitto stimato al valore corrente («Chiudere 1
posizione di alfa e liberare circa 120 USDC?»), senza chiudere nulla prima della conferma.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile,
  nessun duplicato per pagina.
- ADR 0116: la dashboard non ha logica di business che l'API non esponga.
- Componenti esistenti: `features/flow-commands` con `command-confirmation.tsx`, e
  `src/components/ui/confirmation-dialog.tsx`.

## Opzioni considerate

1. Un comando «Incassa i profitti» in `features/flow-commands`, con la conferma condivisa. Il numero di posizioni
   aperte e il valore complessivo vengono dallo stato del flusso che la pagina già legge dall'API; la stima liberata è
   valore complessivo − capitale (attuale, o indicato in un campo facoltativo della conferma). Alla conferma chiama
   `POST /flows/{flow_id}/cash-out`, poi mostra l'importo liberato o le posizioni non chiuse e invalida le letture di
   stato e capitale libero.
2. Una pagina dedicata all'incasso: scartata, perché un comando del flusso vive tra i comandi del flusso.

## Esito della decisione

Opzione 1. Il comando appare solo quando il valore complessivo del flusso supera il capitale allocato; il rifiuto
dell'API si mostra con il componente d'errore condiviso. La sottrazione della stima è la presentazione di due valori
dell'API, non una regola: l'importo vero è quello che restituisce il comando.

Verifica: prova (scenario «Conferma nella dashboard» di R3.4.1 con playwright-bdd, unit test del comando).

### Conseguenze

- Le feature di F3.4 entrano nell'elenco degli scenari di playwright-bdd per gli scenari della dashboard.
