---
paths:
  - "src/autotrading/*/flows/**"
  - "tests/**/flows/**"
  - "specs/E1-flussi-autonomi/F1.1-flussi-di-trading/**"
  - "specs/E1-flussi-autonomi/F1.5-rischio-ed-esecuzione/**"
  - "specs/E1-flussi-autonomi/F1.6-capitale-dei-flussi/**"
  - "specs/E1-flussi-autonomi/F1.7-registrazione-e-consultazione/R1.7.2-*"
---

# Contesto flows

Il flusso di trading: che cosa opera, con quali regole e con quale capitale.

## Glossario

- **Flow**: agente che opera in autonomia su un conto, con nome, asset, intervallo di ciclo, modello IA,
  fonti, istruzioni, limiti di rischio e capitale allocato (R1.1.1).
- **Configuration version**: configurazione immutabile e numerata in ordine crescente; ogni modifica
  accettata ne crea una nuova (R1.1.3). Un ciclo usa la versione letta al suo inizio.
- **Flow status**: `stopped` (fermo), `active` (attivo), `paused` (in pausa, con il motivo se automatica),
  `archived` (archiviato, definitivo) (R1.1.4-R1.1.6).
- **Allocated capital**: quota del saldo del conto assegnata al flusso. **Free capital** del conto: saldo
  letto dall'exchange meno i capitali allocati ai flussi non archiviati (R1.1.7).
- **Funds** (soldi del flusso): capitale allocato, più PnL realizzato e funding, meno le commissioni; base delle
  quote e dei limiti percentuali del rischio (R1.5.1, ADR 0078). **Available liquidity** del flusso: i soldi meno il
  margine delle sue posizioni aperte (R1.6.1). PnL, commissioni e funding vengono dai totali del registro.
- **Ledger** (registro delle operazioni): storico di ogni esecuzione e pagamento di funding di un conto, scritto una
  volta sola, con il flusso a cui appartiene o nessuno; **flow totals**: PnL realizzato, commissioni, funding e
  posizione attesa per asset di un flusso, aggiornati con le sole righe nuove (ADR 0063).
- **Risk limits**: leva massima (obbligatoria) ed esposizione per operazione sul margine e sul valore
  (almeno una), in percentuale dei soldi del flusso; opzione "porta al minimo" (R1.5.1-R1.5.4).
- **Risk outcome** di una decisione: approvata, ridotta, bloccata (R1.5.x); scartata è di `agent` (R1.4.5).
- **Unattributable item**: posizione, esecuzione o variazione di saldo del conto che nessun flusso spiega
  (R1.6.2).
- **Closed position**: posizione di un flusso chiusa, con risultato e motivo di chiusura (R1.7.2).

## Regole

- **Conflitto sugli asset**: due flussi non archiviati dello stesso conto non hanno asset in comune
  (R1.1.2). È ciò che rende una posizione attribuibile al flusso per asset.
- **Nessuna liquidità propria**: lo stato del flusso si ricava da ciò che l'exchange mostra e dal registro delle
  operazioni. Le posizioni si attribuiscono per asset. Un'esecuzione è del flusso del suo ordine; un ordine della
  piattaforma senza flusso è del flusso che ha l'asset; senza ordine della piattaforma solo liquidazione e chiusura
  esatta della posizione attesa sono del flusso dell'asset; il funding è del flusso che ha la posizione (ADR 0063).
  La piattaforma non tocca ciò che non attribuisce.
- Il registro si scrive solo con `RecordAccountExecutionsUseCase`, dalla riconciliazione del conto all'inizio e alla
  fine di ogni ciclo, leggendo dall'exchange solo ciò che è nuovo; il ciclo legge i totali, mai lo storico. Se
  l'exchange non conserva più tutto ciò che è avvenuto dall'ultima lettura, tutti i flussi del conto vanno in pausa
  con il motivo "registro delle esecuzioni incompleto" (ADR 0063).
- All'inizio del ciclo, dopo la riconciliazione, una posizione del conto su un asset del flusso diversa da quella
  attesa dal registro ferma il ciclo prima di ogni ordine e mette in pausa il flusso con il motivo "posizione X
  diversa da quella del flusso: attesa A, sul conto B" (ADR 0064). Prima della pausa il conto si riconcilia
  ancora una volta e il confronto si ripete: la pausa scatta solo se la differenza resta; se le esecuzioni non si
  rileggono il ciclo fallisce senza pausa (ADR 0075). Le esecuzioni degli ordini della procedura di verifica non
  appartengono a nessun flusso.
- Stati e transizioni sono regole del domain: avvia da fermo, pausa da attivo, riprendi da in pausa,
  archivia solo da fermo; un flusso archiviato non si avvia e non si modifica (ADR 0036).
- Il conto di un flusso non cambia mai. Un asset con posizione aperta non si toglie dalla configurazione.
- Lo stop chiude sempre le posizioni del flusso (decisione del proprietario: senza stop loss sull'exchange
  una posizione lasciata aperta non è protetta), dopo il ciclo in corso; ogni posizione chiusa entra nello
  storico col motivo dello stop o della rimozione del conto (ADR 0055).
- Una posizione chiusa a mano (R0.3.2) entra nello storico del flusso che ha l'asset sul conto, col motivo
  "comando manuale", quando l'exchange conferma l'esecuzione (ADR 0061).
- Il capitale allocato cambia in ogni stato tranne archiviato: versione nuova della configurazione più una riga
  di cronologia; un aumento entro il capitale disponibile, una riduzione che non porta sotto zero la liquidità del
  flusso letta dallo stato di R1.6.1 (ADR 0053, ADR 0068).
- Il margine di una posizione è uno solo: quello che l'exchange dichiara (`marginUsed`, `AccountPosition.margin`),
  in ogni controllo e vista; solo lo storico delle posizioni chiuse tiene il margine dell'esecuzione di apertura,
  che l'exchange non dà più dopo la chiusura (ADR 0067).
- Ordine del controllo del rischio: leva, poi esposizione, poi coerenza con lo stato, poi importo minimo.
  Le decisioni di un ciclo si controllano nel loro ordine: ogni apertura approvata impegna il suo margine e le
  successive vedono la liquidità residua; una chiusura non libera liquidità prima dell'esecuzione (ADR 0065).
- Gli ordini passano dal contesto `orders` (apertura, chiusura, esito reale); `flows` non parla con
  l'exchange per inviare ordini.

## Porte del contesto

- `FlowRepositoryPort`: flussi del tenant con la versione di configurazione in vigore; nome unico tra i non
  archiviati (ADR 0031); legge un flusso per id e ogni sua versione, salva lo stato e le versioni nuove
  senza toccare le precedenti (ADR 0036).
- `FlowAccountPort`: exchange e saldo del conto letti ora, dal contesto `accounts` attraverso il `worker`.
- `ModelSettingsPort`, `SourceSettingsPort`: modello e fonti con i parametri risolti, dai contesti `agent` e
  `sources`; un rifiuto arriva come `InvalidFlowSettingError` con il motivo del contesto che lo dà.
- `MarketsPort`: asset negoziabili ora sull'exchange, per nome dell'exchange.
- `AccountActivityPort`: ciò che l'exchange mostra del conto ora (posizioni con margine, movimenti del saldo),
  letto dal `worker` e chiesto dall'API via HTTP interno (ADR 0044, ADR 0063).
- `AccountExecutionsPort`: esecuzioni e funding del conto da un istante, con l'indicazione se la finestra è completa,
  letti dal `worker` (ADR 0063).
- `FlowLedgerPort`: cursore del conto, chiavi già registrate, scrittura delle righe nuove con i totali nella stessa
  transazione, totali dei flussi (ADR 0063).
- `FlowOperationsPort`: storico delle operazioni di un flusso o di un conto (solo fuori da ogni flusso, o tutte), con
  il nome del flusso su ogni riga: pagine di 50 per keyset dalla più recente con i totali del filtro in una sola query
  aggregata, ed esportazione dalla più vecchia letta in streaming; filtri per asset e periodo (ADR 0074, ADR 0080).
- `PlatformOrdersPort`: tra i `cloid` dati, quelli degli ordini registrati sul conto, con il flusso che li ha
  inviati (contesto `orders`).
- `ReconciliationRepositoryPort`: ultima lettura di ogni conto e non attribuibili registrati una volta (ADR 0045).
- `ClosedPositionsPort`: storico delle posizioni chiuse dei flussi (R1.7.2).
- `FlowPositionsPort`: chiusura di una posizione del flusso attraverso il `worker` (fill o rifiuto) (ADR 0055); la
  modifica non toglie un asset con posizione aperta, letta da `AccountActivityPort` (R1.1.3, ADR 0067).
- `FlowOpeningsPort`: ultima apertura eseguita del flusso su un asset, dagli ordini registrati (ADR 0055).
- `RunningCyclePort`: attesa della fine del ciclo in corso; advisory lock PostgreSQL con la chiave `lock_key`
  che l'esecutore dei cicli tiene per tutto il ciclo (ADR 0042, ADR 0055).
- `FlowTimingPort`: ancora dei cicli (ultimo avvio o ripresa) e motivo della pausa automatica di ogni flusso (ADR 0052).
- I bridge verso gli altri contesti vivono solo in `bootstrap.py`; `flows` fornisce ad `agent` i flussi che
  usano una chiave (`ProviderKeyUsageFromFlows`).

Invio degli ordini attraverso `orders` nasce con i requisiti che lo usano.
