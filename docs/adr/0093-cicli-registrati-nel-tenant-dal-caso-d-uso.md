# ADR 0093 — Cicli presi e registrati nel tenant del flusso dal caso d'uso

- Stato: proposta (13 novembre 2026): si discosta dalla decisione del proprietario (adapter SQL che trova il tenant con una query), in attesa di conferma
- Requisiti: R1.2.1-R1.2.5, R1.7.1; Bug B0.0.3 (177)
- Supera: la parte di ADR 0042 e 0046 che affida a `CyclesOfTenants` in `bootstrap.py` la scelta del tenant in cui
  prendere e registrare un ciclo, e il contenitore `CycleRuntime`
- Collegate: ADR 0089 (un adapter, una tecnologia; il caso d'uso orchestra), CLAUDE.md (Regola delle dipendenze)

## Contesto e problema

Il worker pianifica i flussi di tutti i tenant, ma un ciclo si prende (`claim`) e si registra (`record`) sotto row
level security, nel tenant del suo flusso. `CyclesOfTenants`, una classe di `bootstrap.py`, riceveva la porta dei
flussi pianificati, ne leggeva il tenant e apriva il repository SQL di quel tenant: una sequenza dentro un adapter
che riceve una porta, in un file che deve solo collegare. `CycleRuntime` raggruppava tre porte solo per passarle
insieme.

## Opzioni considerate

1. **Il caso d'uso del ciclo sceglie il tenant**: `CycleGuards` porta la porta dei flussi pianificati e la fabbrica
   del repository dei cicli per tenant; `RunCycleUseCase` chiede il tenant del flusso e usa il repository di quel
   tenant.
2. **Adapter SQL che trova il tenant con una query**: la policy della pianificazione mostra solo i flussi attivi,
   quindi un ciclo che mette in pausa il proprio flusso non troverebbe più il tenant per registrarsi; servirebbe una
   policy nuova, cioè una migrazione, per un dato che il worker conosce già.

## Esito della decisione

Opzione 1. La sequenza «tenant del flusso, poi repository di quel tenant» è orchestrazione e sta nel caso d'uso;
l'adapter SQL dei cicli resta quello di un solo tenant e non riceve porte; `bootstrap.py` passa
`partial(SqlAlchemyCycleRepositoryAdapter, engine)` come fabbrica. `CycleRuntime` sparisce: `run_due_cycles` riceve
le porte che usa.

## Conseguenze

- Comportamento invariato: stesso tenant, stessa unicità del ciclo pianificato, stessa registrazione.
- Un test unitario prova che il ciclo di un flusso di un altro tenant si registra nel repository di quel tenant.
- Escono dall'elenco delle violazioni note `bootstrap.py:CyclesOfTenants` e `bootstrap.py:CycleRuntime`.
