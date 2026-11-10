# ADR 0018 — Adapter dei conti: chiavi generate sulla macchina, RLS su PostgreSQL, verifica firmata su Hyperliquid

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.2.1, R0.2.3, R0.1.3

## Contesto

ADR 0017 ha fissato il caso d'uso di registrazione sulle porte `ExchangePort`, `CredentialSealerPort` e
`AccountRepositoryPort`. Servono gli adapter veri e la rotta dell'API. Restano da decidere quattro
cose: come nasce e dove vive la coppia di chiavi (ADR 0007 dice solo "generata sul server"), come la
row level security vede il tenant della richiesta, come si prova su Hyperliquid che le credenziali
funzionano (leggere il saldo richiede solo l'indirizzo, non prova la chiave) e quale versione dell'SDK
si installa su Python 3.15.

## Decisione

- **Coppia di chiavi** generata da `deploy/prepare-installation.sh` al primo rilascio, con l'immagine
  dell'API e PyNaCl, solo se nessuna delle due esiste: privata `credentials_private_key_v1`
  (root, 0400, oggi non montata in nessun container), pubblica `credentials_public_key` (0444),
  entrambe in base64. Se ne manca una sola il rilascio si ferma: una chiave privata non si rigenera
  mai sopra quella esistente, perché renderebbe illeggibili le credenziali salvate. L'API riceve la sola
  pubblica come secret del compose (`CREDENTIALS_PUBLIC_KEY_FILE`) e la versione (`CREDENTIALS_KEY_VERSION`).
- **Testo cifrato**: JSON con `tenant_id`, `account_id`, indirizzo e chiave, cifrato con `SealedBox`.
  La decifratura del `worker` confronterà tenant e conto.
- **Row level security**: tabella `accounts` con `ENABLE` e `FORCE ROW LEVEL SECURITY`, una policy
  `USING` e `WITH CHECK` su `NULLIF(current_setting('app.tenant_id', true), '')::uuid`. Senza tenant
  dichiarato la comparazione è nulla e non si vede nessuna riga. L'adapter apre ogni transazione con
  `set_config('app.tenant_id', <tenant>, true)`: il valore vale solo per quella transazione, quindi una
  connessione del pool non porta il tenant di una richiesta precedente. Vincolo unico `(tenant_id, name)`.
  Un'entità di un altro tenant passata all'adapter solleva `CrossTenantAccessError` prima del database.
- **Verifica su Hyperliquid**: l'adapter firma con la chiave dell'API wallet un `cancelByCloid` di un
  `cloid` casuale a 128 bit sull'asset `BTC`. L'ordine non può esistere, quindi l'exchange non cambia
  nulla, ma risponde `status: ok` solo a un firmatario autorizzato per il conto; altrimenti risponde con
  un errore il cui testo diventa `exchange_message`. Poi legge `clearinghouseState` e riporta
  `marginSummary.accountValue` in USDC. Rete di test in `dev`, reale in `prod`, decisa da `APP_ENVIRONMENT`.
  Errori `4xx` dell'exchange: rifiuto con il suo messaggio; `5xx`, timeout e rete: "exchange non
  raggiungibile, riprovare". Timeout di 10 secondi, nessun nuovo tentativo.
- **Nessuna credenziale nelle risposte**: il messaggio dell'exchange passa al client con indirizzo e
  chiave sostituiti da `***`; gli errori di validazione della richiesta non riportano più l'input;
  la rappresentazione della richiesta mostra solo nome ed exchange.
- **SDK** `hyperliquid-python-sdk` 0.24 con `eth-account` 0.10: dalla 0.11 `eth-account` dipende da
  `ckzg`, che non pubblica wheel per Python 3.15. Ogni dipendenza ha wheel Linux per cp315 o abi3 e
  `pip-audit` non trova vulnerabilità. Si torna alla versione più recente quando `ckzg` pubblica le wheel.
- **API**: `POST /accounts` sul router protetto. 201 con id, nome, exchange e saldo (importo come stringa
  per non perdere precisione); 422 per dati mancanti, exchange non supportato (con `supported`) e
  credenziali rifiutate (con `exchange_message`); 409 per nome in uso; 503 per exchange non raggiungibile.
- **Contratti di import**: domain e application non importano `jwt`, `nacl`, `hyperliquid`,
  `eth_account`, `requests`; le cartelle di tecnologia non si importano a vicenda.

## Alternative scartate

- **Elenco degli agenti approvati (`extraAgents`)**: lettura pura, ma la risposta non è un rifiuto
  dell'exchange e non c'è un suo messaggio da riportare (R0.2.1).
- **Solo lettura del saldo**: prova l'indirizzo, non la chiave.
- **Chiave pubblica come variabile dell'environment GitHub**: la coppia passerebbe da una persona o da
  GitHub, contro ADR 0007.
- **`SET app.tenant_id` di sessione**: resterebbe sulla connessione del pool dopo la richiesta.
- **`eth-account` recente con `ckzg` compilato nell'immagine**: toolchain C nell'immagine di build per
  una funzione (blob EIP-4844) che la piattaforma non usa.

## Conseguenze

- Il comportamento esatto delle risposte di Hyperliquid alla verifica si conferma sulla testnet con
  `tests/integration/hyperliquid/test_exchange_testnet.py` (marker `testnet`) quando esisterà il conto
  di test: passo manuale di fine epica.
- Il `worker` (R0.2.2) monterà la chiave privata e implementerà l'opener sulla versione della chiave.
- R0.1.3 e R0.2.4 aggiungono letture e sostituzione allo stesso adapter, sotto la stessa policy.
