# ADR hyperliquid-testnet-come-adapter-dedicato — Hyperliquid Testnet come adapter dedicato che eredita dall'adapter reale

- Stato: accettata (15 novembre 2026)
- Requisiti: R2.3.11 (User Story 390, Task 391), R2.3.10, R2.3.9
- Sostituisce: ADR 0155 (rete di Hyperliquid dalla configurazione dell'adapter), nella parte che sceglie la rete con
  `HYPERLIQUID_NETWORK`
- Collegate: ADR nome-della-rete-dichiarato-dall-adapter, ADR 0156, ADR 0157, ADR 0158, ADR accessi-del-worker-come-campi-dichiarati

## Contesto e problema

Con l'ADR 0155 ogni installazione sceglie la rete di Hyperliquid con `HYPERLIQUID_NETWORK`: l'exchange si chiama
sempre «Hyperliquid» e la sua rete dipende da dove gira. Il proprietario vuole scegliere la rete scegliendo l'exchange,
con un exchange «Hyperliquid Testnet» selezionabile accanto a «Hyperliquid», offerti entrambi in ogni installazione e
senza variabili. I casi d'uso scelgono già l'adapter dal nome dell'exchange del conto (mappe per nome di
`hyperliquid_adapters`), per lettura dello stato, mercati, ordini, attività ed esecuzioni. Va deciso come nasce
l'exchange di test e da quale rete leggono le fonti di mercato, che non appartengono a un conto.

## Fattori decisionali

- Un adapter = una tecnologia: la testnet è lo stesso sistema integrato su un altro indirizzo.
- Il proprietario: l'adapter di test eredita da quello reale e ridefinisce solo rete e indirizzo (o un decorator, se
  migliore).
- Nessuna decisione in `bootstrap.py`; la dashboard non nomina exchange (R2.3.9).

## Opzioni considerate

### 1. Sottoclassi di test degli adapter che dichiarano la rete, istanze sull'indirizzo di test per gli altri

- Pro: `HyperliquidTestnetExchangeAdapter(HyperliquidExchangeAdapter)` ridefinisce solo `is_real`, `network_name` e
  l'indirizzo predefinito; tutto il resto (sonda delle credenziali, lettura dello stato, controlli di forma) è
  ereditato e non si duplica.
- Pro: gli adapter che non dichiarano una rete (mercati, ordini, attività, esecuzioni) non hanno nulla da
  ridefinire: si costruiscono sull'indirizzo della testnet, come già fanno.
- Contro: due nomi di exchange da tenere allineati nelle mappe per nome.

### 2. Decorator che avvolge l'adapter reale

- Pro: nessuna ereditarietà.
- Contro: la rete è un dato della costruzione (l'indirizzo dell'API), non un comportamento aggiunto attorno a una
  porta; il decorator dovrebbe comunque ricevere un adapter già costruito sulla testnet e inoltrare ogni metodo.

### 3. Tenere `HYPERLIQUID_NETWORK` e offrire l'altro exchange solo se configurato

- Pro: l'installazione decide quali exchange offrire.
- Contro: il proprietario ha scelto entrambi ovunque, senza variabili.

## Esito della decisione

Opzione 1.

- `HyperliquidExchangeAdapter` è l'exchange reale: rete reale, nome «mainnet», API reale.
  `HyperliquidTestnetExchangeAdapter` ne eredita e ridefinisce solo rete di test, nome «testnet» e API della testnet.
- `hyperliquid_adapters` restituisce per ogni porta per conto una mappa con «Hyperliquid» e «Hyperliquid Testnet»,
  ciascuno sul suo indirizzo: ogni caso d'uso che sceglie l'adapter dal nome dell'exchange del conto (registrazione,
  verifica, ciclo, ordini, attività, esecuzioni, mercati) va sulla rete giusta senza cambiare.
- Le fonti di mercato (storico dei prezzi e dati di mercato degli indicatori) non appartengono a un conto e leggono
  l'API reale: descrivono il mercato, e il libro della testnet ha prezzi e volumi non rappresentativi. Gli ordini e i
  controlli di importo minimo restano sull'exchange del conto.
- `HYPERLIQUID_NETWORK` si toglie da configurazione, pipeline e compose; le variabili degli environment `dev` e `prod`
  si cancellano dopo l'integrazione.

### Conseguenze

- Nessun conto è registrato su dev né su prod: nessuna migrazione dei dati. Un conto registrato prima come
  «Hyperliquid» su un'installazione testnet andrebbe registrato di nuovo come «Hyperliquid Testnet».
- L'avviso della rete di test e la conferma del denaro reale seguono l'exchange del conto (R2.3.10, ADR 0156).
