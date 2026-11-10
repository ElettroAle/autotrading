# ADR 0019 — Sostituzione delle credenziali con impronta del conto dell'exchange

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.2.4

## Contesto

R0.2.4 chiede di sostituire le credenziali di un conto senza ricrearlo. Le nuove credenziali devono essere
accettate dall'exchange e devono operare lo stesso conto dell'exchange: credenziali valide di un altro conto
si rifiutano. L'API conosce solo la chiave pubblica (ADR 0007, ADR 0018), quindi non può aprire le
credenziali salvate per confrontare l'indirizzo. Serve un modo di riconoscere il conto dell'exchange senza
tenere l'indirizzo in chiaro (R0.2.3).

## Decisione

- **Impronta del conto dell'exchange**: il conto salva `ExchangeAccount`, lo SHA-256 dell'indirizzo in
  minuscolo, nella colonna `exchange_account_fingerprint` (migrazione 0003, obbligatoria). L'impronta nasce
  alla registrazione. Alla sostituzione si confronta l'impronta delle nuove credenziali con quella salvata,
  prima di chiamare l'exchange: credenziali di un altro conto non escono dalla piattaforma.
- **Ordine della sostituzione**: conto del tenant (altrimenti "non trovato"), credenziali presenti, stesso
  conto dell'exchange, lettura firmata del saldo sull'exchange del conto (stessa verifica della
  registrazione), cifratura, poi `replace`. Ogni rifiuto lascia le credenziali precedenti. Il testo cifrato
  precedente si sovrascrive nella stessa riga: la piattaforma non conserva le credenziali sostituite.
- **Porta del repository**: `AccountRepositoryPort` aggiunge `list`, `get` e `replace`. L'adapter
  PostgreSQL aggiorna per id sotto row level security; se nessuna riga cambia solleva
  `CrossTenantAccessError`.
- **API**: `PUT /accounts/{id}/credentials` con indirizzo e chiave. 200 con il dettaglio del conto; 404 per
  un conto inesistente o di un altro tenant; 422 per credenziali rifiutate (con `exchange_message`
  oscurato), per credenziali di un altro conto e per credenziali mancanti; 503 per exchange non
  raggiungibile.
- **Composizione**: `TenantUseCases.on` costruisce tutti i casi d'uso del tenant dalle stesse porte, per
  `bootstrap` e per gli scenari.

## Alternative scartate

- **Indirizzo in chiaro nella tabella**: rende leggibile il conto dell'exchange a chi legge il database o
  un backup, contro R0.2.3.
- **Confronto nel `worker` con la chiave privata**: porta la chiave privata nel percorso di una richiesta
  dell'utente e un passaggio HTTP interno per una verifica che l'impronta risolve.
- **Nessun controllo, ci si fida dell'exchange**: l'exchange accetta credenziali valide di qualunque conto,
  e il conto della piattaforma cambierebbe conto dell'exchange senza dirlo.
- **Impronta con HMAC e chiave segreta**: l'indirizzo è pubblico sulla blockchain; una chiave in più da
  custodire non protegge un dato già pubblico, protegge solo il legame con il conto, che il tenant già vede.

## Conseguenze

- Un conto creato prima della migrazione 0003 non esiste: l'API rifiuta ogni richiesta finché
  l'autenticazione non è configurata, quindi nessuna riga precede la colonna.
- La sostituzione costa una chiamata firmata all'exchange, come la registrazione.
