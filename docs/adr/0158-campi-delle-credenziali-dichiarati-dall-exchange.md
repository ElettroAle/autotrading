# ADR 0158 — Campi delle credenziali dichiarati dall'adapter dell'exchange

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: R2.3.9 (US 281, Task 282), R0.2.1, R0.2.4, R2.3.1
- Collegate: ADR 0157 (rete nell'elenco degli exchange, di cui estende la risposta), ADR 0152, ADR 0130, ADR 0007

## Contesto e problema

Registrazione e sostituzione delle credenziali di un conto chiedevano `account_address` e `secret_key`: i dati di
Hyperliquid, cablati nel domain, nei comandi, nella richiesta HTTP e nel modulo della dashboard. Un secondo exchange
con credenziali diverse avrebbe richiesto di cambiare ogni livello.

## Opzioni considerate

### 1. L'adapter dichiara i campi, le credenziali sono una mappa validata su quei campi

- Pro: la dashboard genera il modulo dai campi dell'elenco degli exchange; domain e API non conoscono i dati di un
  exchange; un exchange nuovo cambia solo il suo adapter.
- Contro: la forma della richiesta cambia (`credentials: {nome: valore}`).

### 2. Un tipo di credenziali per exchange nel domain

- Pro: tipizzazione forte di ciascun campo.
- Contro: il domain nomina gli exchange; ogni exchange nuovo tocca domain, API e dashboard.

## Esito della decisione

Opzione 1. `ExchangePort.credential_fields()` restituisce i `CredentialField(name, label, secret)` dell'exchange;
`Credentials.declared(fields, values)` rifiuta un campo non previsto (`UnknownCredentialFieldError`, con `field`) e un
campo mancante (`CredentialFieldRequiredError`: «<etichetta> obbligatorio», con `field`); tutti vuoti restano
«credenziali obbligatorio». `GET /exchanges` aggiunge `fields` a ogni exchange; `POST /accounts` e
`PUT /accounts/{id}/credentials` ricevono `credentials` come mappa. Il modulo della dashboard mostra i campi
dell'exchange scelto, i segreti mascherati, e lascia all'API ogni controllo sui loro valori (ADR 0130), che risponde
accanto al campo che nomina. Hyperliquid dichiara «Indirizzo del conto» (`account_address`) e «Chiave dell'API wallet»
(`secret_key`, segreto).

L'impronta del conto (`ExchangeAccount`) è lo SHA-256 dei valori non segreti in minuscolo uniti da a capo: con il solo
indirizzo coincide con quella di prima, quindi nessuna migrazione. Il sigillo contiene i campi dichiarati con
`tenant_id` e `account_id`: i nomi di Hyperliquid restano gli stessi, i conti già registrati si aprono come prima.

Debito: gli oggetti di accesso del worker leggono ancora i nomi dei campi di Hyperliquid nell'opener di libsodium
(Bug 284).

Verifica: prova (scenari di R2.3.9 e R2.3.1, `test_credentials.py`, `test_exchange_account.py`, `test_exchanges.py`,
`test_accounts.py`, `declared-fields.test.tsx`, `register-account-form.test.tsx`).
