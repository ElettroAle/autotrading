---
paths:
  - "src/autotrading/*/accounts/**"
  - "tests/**/accounts/**"
  - "specs/E0-esecuzione-verificata/F0.2-conti-di-trading/**"
---

# Contesto accounts

## Glossario

- **Account** (conto di trading): collegamento a un conto su un exchange, posseduto da un tenant
  (`TenantOwned`). Nome univoco nel tenant.
- **Credentials**: chiavi generate dall'utente sull'exchange. Il database le conserva cifrate con la
  chiave pubblica dell'installazione; solo il `worker` le decifra (R0.2.3, ADR 0007).
- **Account state**: saldo, margine disponibile, posizioni aperte con prezzo di mercato dichiarato dall'exchange (R1.4.7),
  letti dall'exchange.

## Regole

- Le credenziali non compaiono mai in risposte, log, errori o eccezioni: il tipo che le contiene ha
  un `__repr__` che le maschera.
- Le credenziali sono una mappa sui campi che l'adapter dell'exchange dichiara (`ExchangePort.credential_fields()`,
  R2.3.9, ADR 0158): domain, API e dashboard non nominano i dati di un exchange.
- I valori delle credenziali perdono spazi agli estremi e caratteri di formato invisibili (Unicode `Cf`); l'adapter
  dell'exchange ne controlla la forma prima di contattarlo e un valore di forma sbagliata è
  `CredentialFieldMalformedError`, col campo e con che cosa non torna, mai un suo carattere (Bug 387).
- Alla registrazione e alla sostituzione le credenziali si controllano leggendo il saldo prima di
  salvarle (R0.2.1, R0.2.4). Nessun controllo sui permessi di prelievo.
- I campi che l'adapter dichiara non segreti (l'indirizzo del conto) il conto li conserva in chiaro in
  `ExchangeAccount.public_fields` e l'API li mostra; la sostituzione chiede solo i segreti e rifiuta un campo pubblico
  con `PublicCredentialFieldNotReplaceableError`. Un conto registrato prima, senza campi pubblici, li chiede tutti e li
  conserva (Bug 401, ADR campi-pubblici-del-conto-conservati-in-chiaro).
- Il conto non ha un attributo test/reale: la rete è quella dell'exchange che il conto dichiara. Hyperliquid e
  Hyperliquid Testnet sono due exchange offerti in ogni installazione, senza configurazione (R2.3.11, ADR
  hyperliquid-testnet-come-adapter-dedicato); `ExchangePort.is_real()` dice la rete ai casi d'uso (ADR 0155),
  `ExchangePort.network_name()` col nome che le dà l'exchange (R2.3.10, ADR nome-della-rete-dichiarato-dall-adapter).
- La rimozione di un conto è un caso d'uso del contesto `flows` (`RemoveAccountWithFlowsUseCase`, ADR 0090):
  `accounts` definisce solo che cosa significa rimuovere (credenziali cancellate, conto nascosto, storico
  conservato, ADR 0025), realizzato da `SqlAlchemyAccountRepositoryAdapter.remove_account`.

## Porte del contesto

`ExchangePort` (lettura di saldo e stato), `CredentialSealerPort` e `CredentialOpenerPort` (cifratura e decifratura delle credenziali), `AccountRepositoryPort`.
