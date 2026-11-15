# ADR credenziali-senza-caratteri-invisibili-e-forma-diagnosticabile — Credenziali senza caratteri invisibili e forma dei campi Hyperliquid diagnosticabile

- Stato: accettata (15 novembre 2026)
- Requisiti: Bug 387 (Task 388), R0.2.1, R2.3.9
- Collegate: ADR 0158, ADR errori-del-contratto-per-campi-mancanti, ADR 0027

## Contesto e problema

Il proprietario registra un conto Hyperliquid con una chiave dell'API wallet che conferma corretta, e l'API autorizzata
per quel conto sulla testnet. La registrazione risponde «chiave dell'API wallet non valida»: `eth_account` non
riconosce il valore come chiave e il rifiuto nasce prima di contattare l'exchange. Il motivo non dice che cosa non
torna. Il domain toglie gli spazi agli estremi (`Credentials.declared`), ma un valore copiato da un password manager o
da una pagina web può portare caratteri invisibili che non sono spazi: spazio a larghezza zero, BOM, joiner (categoria
Unicode `Cf`). Una chiave così è identica a vista e rifiutata. Va deciso dove si ripulisce il valore e come il
rifiuto di forma diventa leggibile, senza mai mostrare il segreto.

## Fattori decisionali

- Le credenziali non compaiono mai in risposte, log o errori (R0.2.3).
- Domain, API e dashboard non nominano i dati di un exchange (R2.3.9, ADR 0158).
- Il valore salvato è quello che ogni adapter legge: ripulirlo in un solo adapter lascerebbe sporchi gli altri
  percorsi (ordini, attività, esecuzioni).
- Un errore dell'adapter è un errore del contratto della sua porta.

## Opzioni considerate

### 1. Il domain toglie i caratteri invisibili, l'adapter controlla la forma dei suoi campi

- Pro: nessuna credenziale di nessun exchange contiene caratteri di formato invisibili, quindi la pulizia è generica e
  vale prima del sigillo: il valore cifrato è già pulito per ogni lettore.
- Pro: solo l'adapter sa che una chiave Hyperliquid è esadecimale di 64 cifre e un indirizzo di 40; il motivo dice
  la forma attesa e che cosa non torna (lunghezza, caratteri non esadecimali), mai un carattere del valore.
- Contro: il domain conosce una regola di testo in più, generica.

### 2. L'adapter Hyperliquid ripulisce e controlla tutto

- Pro: il domain non cambia.
- Contro: il valore salvato resta sporco e ogni adapter della cartella (ordini, attività, esecuzioni) dovrebbe
  ripulirlo a ogni lettura.

### 3. Lasciare il controllo a `eth_account` e mostrare solo il motivo

- Pro: nessun codice nuovo nell'adapter.
- Contro: una chiave corretta con un carattere invisibile resta rifiutata; il motivo resta muto sulla causa.

## Esito della decisione

Opzione 1.

- `Credentials.declared` toglie da ogni valore i caratteri Unicode di categoria `Cf` oltre agli spazi agli estremi.
- L'adapter Hyperliquid controlla la forma dei due campi prima di contattare l'exchange: chiave dell'API wallet di
  64 cifre esadecimali con o senza `0x`, indirizzo del conto `0x` più 40 cifre esadecimali. Un valore di forma
  sbagliata solleva `CredentialFieldMalformedError`, sottoclasse di `ExchangeRejectedCredentialsError` dichiarata nel
  contratto di `ExchangePort`: porta il campo (`field`) e il motivo, per esempio «chiave dell'API wallet non valida:
  attese 64 cifre esadecimali, con o senza 0x; ricevuti 42 caratteri». Essendo un rifiuto delle credenziali, ciclo e
  verifica la traducono come ogni rifiuto; `read_state_proving` ne conserva il campo quando ne oscura il motivo.
- Gli accessi che il worker apre vengono da credenziali già controllate alla registrazione o alla sostituzione: gli
  adapter di ordini, attività ed esecuzioni restano come sono.

### Conseguenze

- La risposta della registrazione nomina il campo sbagliato: la dashboard lo mostra accanto al campo (ADR 0131).
- Lunghezza e numero di caratteri non esadecimali non rivelano il segreto.
