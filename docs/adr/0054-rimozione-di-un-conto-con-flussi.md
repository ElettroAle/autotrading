# ADR 0054 — Rimozione di un conto con flussi

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.1.8 (Task T1.1.8.1), estende R0.2.5 (ADR 0025)

## Contesto

Rimuovere un conto su cui operano flussi attivi o in pausa chiede una conferma che li nomina; confermata, ferma i
flussi chiudendo le loro posizioni, rimuove il conto e archivia i flussi; una posizione che l'exchange non chiude
lascia il conto, perché senza di esso nessuno potrebbe più chiuderla dalla piattaforma (R1.1.8). I flussi sono di
`flows`, i conti di `accounts`: i contesti si parlano solo in `bootstrap.py`.

## Decisione

- **Porta** `AccountFlowsPort` in `application/accounts` (`operating`, `stop`, `archive`), ponte
  `AccountFlowsFromFlows` in `bootstrap.py` sopra `StopFlowUseCase` (motivo `ACCOUNT_REMOVAL`, ADR 0055) e
  `ArchiveFlowUseCase`.
- **`RemoveAccountUseCase`**: senza conferma controlla prima i flussi (`OperatingFlowsNeedConfirmationError`, 409,
  coi nomi) e poi le posizioni (R0.2.5); con conferma ferma i flussi, e se resta una posizione aperta solleva
  `FlowPositionsLeftOpenError` (409, asset e motivo) senza rimuovere; altrimenti rimuove il conto e archivia i
  flussi fermi del conto.
- `RemoveAccountCommand` porta l'utente, a cui si attribuiscono gli ordini di chiusura.

## Alternative scartate

- **Rimuovere comunque e lasciare le posizioni**: vale per le posizioni manuali di R0.2.5, non per quelle dei
  flussi, che la piattaforma gestisce.
- **Archiviare prima di rimuovere**: un errore nella rimozione lascerebbe flussi archiviati su un conto vivo.

## Conseguenze

- Ogni posizione chiusa dalla rimozione entra nello storico col motivo "rimozione del conto" (R1.7.2).
- I flussi di un conto rimosso restano consultabili archiviati.
