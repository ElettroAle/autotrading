# ADR 0097 — Il conto del ciclo si legge con porte del contesto flows

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.2.3, R1.2.4, R1.4.3, R1.6.1; Bug 170, Bug B0.0.3 (177)
- Supera: ADR 0042 nella parte in cui lo stato del flusso del ciclo si legge con `ReadExchangeStateUseCase` del
  contesto `accounts` attraverso `FlowStateFromFlows` in `bootstrap.py`
- Collegate: ADR 0088 (porte del consumatore), ADR 0089 (un adapter, una tecnologia; niente ponti), ADR 0094
  (ciclo nel contesto flows), ADR 0096 (ciclo composto per il tenant)

## Contesto e problema

Il primo passo del ciclo legge il conto del flusso sull'exchange provando le credenziali, riconcilia il conto e
calcola lo stato attribuito al flusso. La sequenza stava in `FlowStateFromFlows`, un ponte di `bootstrap.py` che
usava un caso d'uso e gli errori del contesto `accounts`; `CycleFlow` era una classe di `bootstrap.py` con le regole
della liquidità e del rischio.

## Decisione

- `CycleFlow`, `CycleAccount`, `CyclePosition` e `CycleAccess` sono tipi di `domain/flows`.
- `flows` dichiara `CycleAccessOpenerPort` (credenziali aperte per il ciclo) e `CycleAccountReaderPort` (lettura del
  conto provando le credenziali), con gli errori di `flows`: `FlowCredentialsNotOpenedError`,
  `FlowCredentialsRefusedError`, `FlowExchangeUnavailableError`. Le realizzano
  `SodiumCredentialOpenerAdapter.open_cycle_access` e `HyperliquidExchangeAdapter.cycle_reading`, come per la
  verifica (ADR 0088).
- `ReadCycleAccountUseCase` orchestra conto, apertura e lettura e traduce un rifiuto in
  `FlowCredentialsRejectedError` del conto (errore permanente, R1.2.4); `ReadCycleFlowUseCase` compone il flusso del
  ciclo; `StartCycleFlowUseCase` ed `EndCycleFlowUseCase` riconciliano il conto e leggono il flusso all'inizio e alla
  fine del ciclo. La porta dello stato si divide in `CycleStartPort` e `CycleEndPort`.

## Confronto con le decisioni scritte

- CLAUDE.md, «Regola delle dipendenze» (righe 95-108): `flows` non importa `accounts`; le librerie restano nei loro
  adapter; conforme.
- CLAUDE.md, «Principi di codice» (righe 167-190): l'errore della libreria si traduce nell'adapter nell'errore della
  porta; il caso d'uso traduce l'errore del contratto in quello del conto; conforme.
- `docs/architecture.md` §5 (ciclo come grafo LangGraph): non toccato; il passaggio a LangGraph è un lavoro
  successivo.

## Conseguenze

- Escono da `bootstrap.py` `FlowStateFromFlows` e `CycleFlow`; `TenantCyclePorts` perde le porte che servivano solo
  al ponte.
- Comportamento invariato: stesse letture, stesso errore permanente, stessi messaggi.
