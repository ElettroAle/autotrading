# ADR 0017 — Registrazione del conto verificata dall'exchange prima della cifratura

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.2.1, R0.2.3

## Contesto

R0.2.1 chiede di salvare nel tenant un conto con le sue credenziali solo se l'exchange le accetta,
riportando il saldo letto in quel momento, e di rifiutare con motivi precisi: dati mancanti, exchange
non supportato, nome già in uso nel tenant, credenziali rifiutate (con il messaggio originale
dell'exchange), exchange non raggiungibile. ADR 0007 fissa la cifratura con la sola chiave pubblica
lato `api` e il formato salvato con la versione della chiave. Restano da decidere la forma del
dominio, l'ordine dei controlli e dove vive l'elenco degli exchange supportati.

## Decisione

- **Dominio `accounts`**: `Account` estende `TenantOwned` e porta solo `SealedCredentials`
  (versione della chiave e testo cifrato), mai le credenziali in chiaro. `Credentials` (indirizzo
  del conto e chiave segreta) maschera la propria rappresentazione. `AccountName`, `ExchangeName`
  e `Credentials` rifiutano i valori vuoti con "nome obbligatorio", "exchange obbligatorio",
  "credenziali obbligatorio".
- **Ordine in `RegisterAccountUseCase`**: dati, exchange supportato, nome libero nel tenant, saldo
  letto dall'exchange con le credenziali della richiesta, cifratura, salvataggio. I controlli che non
  costano una chiamata di rete vengono prima; nulla si salva se l'exchange non risponde o rifiuta.
- **Exchange supportati = gli adapter collegati** in `bootstrap`: il caso d'uso riceve una mappa nome
  → `ExchangePort`. L'errore "exchange non supportato" elenca le chiavi della mappa, quindi elenco e
  capacità reale non possono divergere.
- **Porte legate al tenant**: `AccountRepositoryPort` e `CredentialSealerPort` si costruiscono per il
  tenant della richiesta; il caso d'uso riceve il `TenantId` dal costruttore, mai dal comando. Il
  nome già in uso si controlla prima della chiamata all'exchange e di nuovo al salvataggio, dove il
  repository traduce la violazione del vincolo in `AccountNameInUseError` (due richieste concorrenti).
- **Errori del contratto** in `application/accounts/errors.py`: `ExchangeRejectedCredentialsError`
  porta `exchange_message`, il testo dell'exchange; `UnsupportedExchangeError` porta `supported`.

## Alternative scartate

- **Salvare prima e verificare dopo**: un conto con credenziali non valide resterebbe nel tenant se la
  verifica fallisse a metà.
- **Elenco degli exchange come costante del dominio**: potrebbe nominare un exchange senza adapter.
- **`tenant_id` nel comando**: contraddice la regola delle porte legate al tenant e lascia a chi
  chiama la scelta del tenant.

## Conseguenze

- Gli adapter veri (cifratura libsodium, PostgreSQL con row level security, Hyperliquid) e la rotta
  dell'API arrivano nella PR successiva con l'ADR della loro tecnologia; questa PR prova il requisito
  sui casi d'uso con gli adapter finti, come chiede la regola dei test.
- R0.2.4 (sostituzione delle credenziali) riusa lo stesso ordine: verifica, cifratura, salvataggio.
