# ADR 0157 — Rete dell'exchange visibile alla registrazione del conto

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: Bug 277 (Task 280), R2.3.1
- Collegate: ADR 0152 (elenco degli exchange supportati, di cui estende la risposta), ADR 0153 (campo di scelta da
  elenco), ADR 0155 (rete dalla configurazione dell'adapter), ADR 0130 (moduli dei conti), ADR 0116

## Contesto e problema

Registrando un conto l'utente non vede se l'exchange scelto opera sulla rete reale. `GET /exchanges` (ADR 0152)
elenca gli exchange supportati per nome soltanto; il nome usato dalla piattaforma finta della dashboard (`hyperliquid`)
non coincideva con quello che l'API accetta (`Hyperliquid`).

## Opzioni considerate

### 1. `GET /exchanges` con nome e rete, avviso nel modulo

- Pro: la rete viene dalla porta dell'exchange, non dedotta dalla dashboard; un solo elenco serve la tendina e l'avviso;
  è la base per i campi delle credenziali dichiarati dall'adapter (US 281).
- Contro: cambia la forma della risposta di ADR 0152 (da nomi a oggetti).

### 3. Endpoint separato per la rete

- Pro: la risposta di ADR 0152 resta invariata.
- Contro: due letture per lo stesso elenco, da tenere allineate.

### 2. Ambiente dell'installazione nell'intestazione

- Pro: esiste già.
- Contro: l'ambiente non è più la rete (ADR 0155).

## Esito della decisione

Opzione 1. `ListSupportedExchangesUseCase` (ADR 0152) restituisce gli exchange per nome con la rete letta da
`ExchangePort.is_real()`; `GET /exchanges` risponde `[{name, network}]` al posto dei soli nomi. Il modulo «Nuovo conto»
offre gli exchange dell'elenco nel campo di scelta (ADR 0153) e, se quello scelto è sulla rete reale, mostra «Il conto
opererà con denaro reale». La piattaforma finta usa il nome reale `Hyperliquid`, anche negli scenari di R2.3.8.

Verifica: prova (scenario di R2.3.1, `test_exchanges.py`, `register-account-form.test.tsx`).
