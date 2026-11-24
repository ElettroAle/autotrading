# ADR exchange-simulato-con-porte-di-lettura-e-scrittura — Exchange simulato: porte dell'exchange divise in lettura del mercato e operazioni del conto

- Stato: proposta (22 novembre 2026)
- Requisiti: US 407 R6.3.2 (Task 408, 409, 410)
- Collegate: ADR 0152 (elenco degli exchange supportati), ADR 0157 (rete dell'exchange alla registrazione), ADR 0158
  (campi delle credenziali dichiarati dall'exchange), ADR 0007 (credenziali solo nel worker), ADR 0066, ADR 0083;
  `.claude/rules/context-orders.md`, `.claude/rules/context-accounts.md`, `.claude/rules/tech-hyperliquid.md`,
  `.claude/rules/tech-sqlalchemy.md`
- Verifica: prova

## Contesto e problema

R6.3.2 vuole un exchange simulato con il mercato vero: prezzi, candele e regole del mercato da Hyperliquid mainnet in
sola lettura, ordini eseguiti in simulazione su un saldo virtuale per tenant conservato dopo un riavvio. Il simulato
unisce due sistemi (Hyperliquid per il mercato, PostgreSQL per lo stato del conto) e per `CLAUDE.md` un adapter usa un
solo sistema, le cartelle adapter non si importano e un adapter non riceve porte. Le porte di exchange di oggi mescolano
la lettura del mercato (`market`) con le operazioni del conto (posizioni, leva, ordini, protezioni, stato del conto).

## Fattori decisionali

- Decisione del proprietario (22 novembre 2026, in chat): interface segregation. Ogni porta di exchange si divide in
  una porta che legge i dati del mercato e una che opera sul conto; due porte, due adapter. L'adapter Hyperliquid
  reale resta uno solo e realizza entrambe le porte.
- `CLAUDE.md`: un adapter = un sistema; il caso d'uso orchestra gli adapter; regole di business nel domain; dati del
  tenant con RLS dentro l'adapter `sqlalchemy/`.
- ADR 0152: un exchange è una voce della mappa degli exchange composta nel bootstrap, col suo nome.
- ADR 0158: i campi delle credenziali li dichiara l'exchange.

## Decisione

- **Porte divise** (in `application/orders/ports.py` e, dove serve, in `application/accounts/ports.py`):
  - porta di **lettura del mercato** (es. `MarketReaderPort`): regole del mercato dell'asset (importo minimo, passi di
    prezzo e quantità, leva massima, commissioni) e prezzo corrente (medio e oracolo), senza credenziali;
  - porta delle **operazioni del conto** (es. `OrderExchangePort`, più `ProtectionExchangePort` e la lettura dello
    stato del conto): posizione, leva, ordine a mercato, ricerca dell'ordine, protezioni, stato del conto, con
    l'accesso del conto. L'ordine a mercato riceve dal caso d'uso il prezzo corrente letto dalla porta di lettura.
  - I casi d'uso ricevono le due porte e orchestrano: leggono il mercato, poi operano sul conto.
- **Selezione dell'exchange**: la mappa degli exchange composta nel bootstrap (ADR 0152) resta una sola, dal nome alla
  **coppia** delle porte: una dataclass frozen in application (es. `ExchangeConnection(market, account)`, con le altre
  porte del conto come campi della stessa coppia). Il caso d'uso legge l'exchange del conto, prende la coppia e usa
  `market` per leggere e `account` per operare. Un nome dà sempre entrambe le porte: nessuna mappa parallela da tenere
  allineata.
- **Hyperliquid reale**: l'adapter di oggi realizza entrambe le porte; comportamento invariato.
- **Exchange simulato**, nome `simulato` nella mappa degli exchange (ADR 0152), rete «simulato» (ADR 0157):
  - lettura del mercato: un adapter Hyperliquid configurato su mainnet, in sola lettura e senza credenziali;
  - operazioni del conto: `SqlAlchemySimulatedExchangeAdapter` in `adapters/outbound/sqlalchemy/`, che esegue con il
    motore del domain e conserva saldo virtuale, posizioni, ordini, protezioni e storico in tabelle proprie con RLS
    (migrazione Alembic). Nessuna credenziale: l'exchange dichiara zero campi (ADR 0158) e la registrazione accetta
    credenziali vuote solo per un exchange che non ne dichiara; l'apertura delle credenziali nel worker non si chiama
    per un conto senza credenziali.
- **Motore di esecuzione** in `domain/orders/simulation/` (Decimal, solo libreria standard), riusabile dal replay
  (R4.2.3): eseguibilità secondo le regole del mercato con lo stesso errore tipizzato dell'exchange vero, prezzo di
  esecuzione = prezzo corrente con slippage configurabile, commissione, margine e leva, prezzo di liquidazione, esito di
  stop loss e take profit dato un prezzo.
- **Stop loss, take profit e liquidazione sui prezzi reali**: un caso d'uso pianificato (con il pianificatore
  esistente del worker) legge i prezzi correnti dalla porta di lettura per le posizioni simulate aperte e chiede alla
  porta di regolamento del simulato (porta propria, realizzata solo dal simulato) di chiudere quelle colpite.
- **Saldo virtuale**: indicato alla registrazione del conto simulato; comando di azzeramento con un nuovo saldo (API e
  pagina del conto nella dashboard) che chiude ogni posizione simulata e cancella ordini e protezioni del conto.
- Il resto della piattaforma (ciclo, rischio, viste, classifica) non distingue un conto simulato.

## Alternative scartate

- Nuovo contesto `simulation`, decorator che sostituisce l'esecuzione, cartella `simulated_exchange/` con due sistemi:
  superate dalla decisione del proprietario.

## Conseguenze

- Ogni caso d'uso che oggi usa le porte di exchange riceve due porte; il bootstrap compone per ogni exchange la coppia.
- Il replay di R4.2.3 riusa il motore del domain senza toccare l'adapter.
