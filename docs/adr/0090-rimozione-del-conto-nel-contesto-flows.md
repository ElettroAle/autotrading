# ADR 0090 — La rimozione del conto è un caso d'uso del contesto flows

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.2.5, R1.1.8; Bug B0.0.1 (173)
- Collegate: ADR 0025 (rimozione logica del conto), ADR 0054 (rimozione del conto con i suoi flussi, di cui supera
  la parte «ponte»), ADR 0055 (stop del flusso), ADR 0087, ADR 0088, ADR 0089

## Contesto

La rimozione di un conto (`RemoveAccountUseCase` del contesto `accounts`) chiedeva a una porta `AccountFlowsPort` di
elencare, fermare e archiviare i flussi del conto. Quella porta era realizzata in `bootstrap.py` da
`AccountFlowsFromFlows`, una classe che chiamava tre casi d'uso di `flows`. Le regole dell'ADR 0089 vietano classi
e ponti in `bootstrap.py` e adapter che ricevono casi d'uso; il contratto di indipendenza vieta ad
`application/accounts` di importare `flows`. Fermare un flusso è un comando che chiude posizioni, non la lettura di
un dato: nessun adapter può realizzarlo.

## Decisione (del proprietario)

- La sequenza «ferma i flussi del conto, rimuovi il conto, archivia i flussi» è il caso d'uso
  `RemoveAccountWithFlowsUseCase` del contesto `flows`, che riceve `StopFlowUseCase` e `ArchiveFlowUseCase` dello
  stesso contesto.
- Per il conto, `flows` dichiara le sue porte nel proprio `ports.py`, raccolte in `AccountRemovalPorts`:
  - `FlowAccountPositionsPort.open_positions_of` (gli asset delle posizioni aperte, R0.2.5), realizzata da
    `HttpxAccountStateAdapter`, che traduce gli errori di `accounts` in `FlowAccountNotFoundError` e
    `FlowExchangeUnavailableError`;
  - `FlowAccountRemovalPort.has_account` e `remove_account`, realizzate da `SqlAlchemyAccountRepositoryAdapter`,
    che applica la rimozione logica del contesto `accounts` (ADR 0025) e solleva `AccountToRemoveNotFoundError`.
- `AccountToRemoveNotFoundError` risponde «non trovato», come ogni rotta dei conti (R0.1.3).
- Le regole di conferma e di posizioni rimaste aperte passano da `domain/accounts/removal.py` a
  `domain/flows/account_removal.py`, con i loro errori, invariati nei messaggi e negli stati HTTP.
- La rotta `DELETE /accounts/{id}` chiama `RemoveAccountWithFlowsUseCase`.
- Spariscono `RemoveAccountUseCase`, `AccountFlowsPort`, `AccountRepositoryPort.remove`, `AccountFlowsFromFlows`,
  `ListAccountFlowsUseCase` e `ArchiveAccountFlowsUseCase`.

## Alternative scartate

- **Caso d'uso di coordinamento fra contesti**: richiederebbe un'eccezione al contratto di indipendenza.
- **Sequenza nella rotta FastAPI**: la sequenza starebbe in un adapter, fuori dal caso d'uso.
- **Classe in bootstrap che chiama i casi d'uso**: vietata dall'ADR 0089.

## Conseguenze

- `tests/architecture/known_violations.py` non contiene più voci del Bug 173.
- Il comportamento visibile non cambia: stessi scenari di R0.2.5 e R1.1.8, stessi messaggi e stati HTTP.
- `SqlAlchemyAccountRepositoryAdapter` realizza una porta in più del contesto `flows`, come prevede l'ADR 0088.
