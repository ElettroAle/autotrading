# ADR 0098 — Gli ordini del ciclo passano per porte del consumatore

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.5.5, R1.7.2, R1.8.2; Bug 170, Bug B0.0.3 (177)
- Supera: ADR 0042 nella parte in cui gli ordini approvati arrivano al contesto `orders` attraverso
  `OrdersFromOrders` in `bootstrap.py`
- Collegate: ADR 0088 (porte del consumatore), ADR 0089 (niente ponti), ADR 0094 (ciclo nel contesto flows)

## Contesto e problema

Il passo di esecuzione del ciclo trasformava gli esiti approvati dal rischio in ordini del contesto `orders`, li
inviava e poi li faceva seguire (notifiche, chiusure registrate): una sequenza tra due contesti scritta in un ponte
di `bootstrap.py`, con `CycleOrder` come classe di `bootstrap.py`.

## Decisione

- `CycleOrder` e `CycleOrders` sono tipi di `domain/flows`. `flows` dichiara `CycleOrderExecutionPort`;
  `SendCycleOrdersUseCase` raccoglie gli ordini approvati del ciclo per il conto del flusso.
- `orders` dichiara `CycleOrdersPort` e `ApprovedOrderPort` (la forma con cui riceve gli ordini approvati, con
  `order_with` come già gli esiti del rischio); `ExecuteCycleOrdersUseCase` invia gli ordini
  (`ExecuteFlowOrdersUseCase`) e poi li segue (`FollowFlowOrdersUseCase`). Lo soddisfa strutturalmente la porta di
  `flows`: nessun contesto importa l'altro e `bootstrap.py` collega soltanto.

## Confronto con le decisioni scritte

- CLAUDE.md, «Comunicazione tra contesti» (righe 93-94): chiamata in-process attraverso porte e casi d'uso esposti;
  conforme.
- CLAUDE.md, «Regola delle dipendenze» (righe 95-108): `flows` e `orders` non si importano; conforme.
- `docs/architecture.md` §5 (ciclo come grafo LangGraph): non toccato; il passaggio a LangGraph è un lavoro
  successivo.

## Conseguenze

- Escono da `bootstrap.py` `OrdersFromOrders` e `CycleOrder`. Comportamento invariato: stesso ordine di invio,
  stesse notifiche, nessun invio senza ordini approvati.
