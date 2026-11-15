# ADR accessi-del-worker-come-campi-dichiarati — Accessi del worker come campi dichiarati dall'exchange

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 284 (Task 293), R2.3.9, R0.3.2, R0.4.1, R1.2.4, R1.6.1
- Collegate: ADR 0158 (di cui chiude il debito dichiarato), ADR 0044, ADR 0007

## Contesto e problema

Dopo R2.3.9 le credenziali di un conto sono una mappa sui campi che l'adapter dell'exchange dichiara (ADR 0158). Gli
accessi che il worker apre per ordini, ciclo, verifica e lettura del conto si costruivano però leggendo per nome
`account_address` e `secret_key` nell'adapter libsodium: un exchange con campi diversi si sarebbe registrato, ma il
worker non ne avrebbe aperto l'accesso. La lettura del conto per i flussi apre solo l'indirizzo, perché il segreto
non esca dall'opener quando non serve (ADR 0044).

## Opzioni considerate

### 1. Accessi come mappa; la lettura apre solo i campi che il lettore dell'exchange dichiara

- Pro: opener e domain non nominano campi di un exchange; resta il minimo privilegio della lettura.
- Contro: un metodo in più sulle porte dei lettori di attività ed esecuzioni.

### 2. Accessi come mappa; la lettura riceve tutti i campi

- Pro: più semplice.
- Contro: il segreto arriva anche a chi legge solo dati pubblici, contro ADR 0044.

### 3. Lasciare i nomi nell'opener

- Pro: nessun lavoro.
- Contro: è il difetto.

## Esito della decisione

Opzione 1. `TradingAccess`, `CycleAccess` e `VerificationAccess` portano i campi aperti come mappa immutabile e
mascherata, con `value(nome)`; un accesso vuoto o con un campo vuoto è rifiutato. La lettura del conto dei flussi
riceve un `AccountReference` con i soli campi che il lettore dichiara (`ActivityReaderPort.reference_fields()`,
`ExecutionsReaderPort.reference_fields()`): `ReferenceOpenerPort.open_reference(sealed, names)` sostituisce
`AddressOpenerPort.open_address` e rifiuta un campo nominato che le credenziali non hanno
(`FlowCredentialsMissingError`). L'opener restituisce i campi del documento cifrato così come sono stati sigillati.
Solo l'adapter Hyperliquid conosce i nomi dei suoi campi; i suoi lettori dichiarano il solo indirizzo.

### Conseguenze

- I documenti cifrati esistenti si aprono senza migrazione: le loro chiavi sono già i nomi dei campi di Hyperliquid.
- Un exchange nuovo dichiara i campi delle credenziali e quelli che servono a leggerne un conto; opener, casi d'uso e
  domain non cambiano.
- La sequenza dei flussi descritta in ADR 0088 resta, con `ReferenceOpenerPort` al posto di `AddressOpenerPort`.
