# ADR 0024 — Procedura di verifica nel worker, nel contesto verification

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.4.1

## Contesto

R0.4.1 chiede una procedura che, su un conto dell'utente, apre una posizione long su BTC con leva 2
per 12 USDC, legge lo stato, chiude la posizione e rilegge lo stato. Ogni passo ha il suo esito, la
procedura ha un esito complessivo, e tutto si registra con utente, conto, ambiente e istante. Non parte
con una posizione già aperta su BTC o con meno di 12 USDC di margine disponibile. Un passo fallito
interrompe la procedura (regola del contesto `verification`).

Apertura, chiusura e lettura usano le credenziali, che apre solo il `worker` (ADR 0021). I casi d'uso
esistono già: `OpenPositionUseCase` e `CloseExchangePositionUseCase` in `orders` (ADR 0022, ADR 0023),
`ReadExchangeStateUseCase` in `accounts` (ADR 0021). La regola del contesto vieta di importare gli
interni di `accounts` e `orders`.

## Decisione

- **Due casi d'uso, come per lettura e chiusura.**
  - `RunVerificationUseCase` (API) chiede la procedura alla porta `VerificationPort` e restituisce la
    procedura registrata.
  - `RunExchangeVerificationUseCase` (`worker`):
    1. lettura iniziale: se c'è una posizione su BTC, `VerificationNotStartedError` "posizione già
       aperta su BTC"; se il margine disponibile è sotto 12 USDC, "margine insufficiente: servono
       almeno 12 USDC". In entrambi i casi nessun ordine e nessuna registrazione: la procedura non è
       partita;
    2. passi "apertura long BTC leva 2", "lettura dopo apertura", "chiusura", "lettura dopo chiusura";
       il primo che fallisce interrompe la procedura;
    3. registrazione con utente, conto, ambiente, istante, esito di ogni passo ed esito complessivo.
- **Esiti.**
  - Apertura e chiusura riescono con un ordine eseguito, anche in parte. Un rifiuto porta il messaggio
    originale dell'exchange, un esito sconosciuto lo dice.
  - "lettura dopo apertura" riesce se legge una posizione long su BTC con leva 2; "lettura dopo
    chiusura" se non legge posizioni su BTC. Ogni lettura registra saldo, margine e posizioni letti.
  - Esito complessivo "superata", oppure "fallita al passo <passo>". Commissione totale e profitto o
    perdita realizzati sono la somma dei due ordini.
  - Se l'apertura è riuscita e la chiusura no, l'esito avverte che resta aperta una posizione long su BTC.
  - Un guasto durante un passo (exchange non raggiungibile, credenziali rifiutate) fa fallire il passo con
    il suo messaggio; durante la lettura iniziale la procedura non parte.
- **Porte proprie del contesto** in `application/verification/ports.py`: `AccountReadingPort` (saldo,
  margine, posizioni in tipi di `verification`), `OrderExecutionPort` (apre e chiude, restituisce un
  `OrderResult`), `VerificationRunRepositoryPort`. In `bootstrap.py` `AccountReadingFromAccounts` e
  `OrderExecutionFromOrders` le collegano ai casi d'uso di `accounts` e `orders`. Gli errori di quei
  contesti diventano `VerificationStepError` con il loro messaggio, o `VerificationAccountNotFoundError`.
- **Origine degli ordini**: entrambi gli ordini portano l'origine "procedura di verifica" e l'utente.
  `CloseExchangePositionCommand` riceve quindi l'`OrderSource` invece del solo utente.
- **HTTP interno**: `POST /tenants/{tenant}/accounts/{conto}/verifications` sul `worker`, con l'utente nel
  corpo e lo stesso token. `HttpxVerificationAdapter` ha un timeout di 120 secondi: la procedura fa una
  decina di chiamate all'exchange, ciascuna fino a 10 secondi.
- **API**: `POST /accounts/{conto}/verifications` restituisce 200 con la procedura anche quando fallisce
  (l'esito è il risultato), 409 quando non parte, 404 per un conto che non è del tenant.
- **Persistenza**: tabella `verification_runs` (migrazione 0005), con RLS per tenant, chiave esterna
  composta (conto, tenant) e solo `SELECT` e `INSERT`. Gli esiti dei passi stanno in una colonna JSON:
  si leggono sempre insieme alla procedura e non si interrogano da soli.
- **Ambiente**: quello dichiarato dal `worker` (`APP_ENVIRONMENT`), registrato con la procedura.

## Alternative scartate

- **Procedura nell'API, che chiama il `worker` passo per passo**: tre rotte interne in più e una procedura
  spezzata su due servizi, con il rischio di lasciare la posizione aperta per una caduta della rete a metà.
- **Tabella dei passi separata**: nessuna interrogazione la richiede; una riga per procedura basta.
- **Procedura che chiude comunque dopo una lettura fallita**: la regola del contesto vuole che un passo
  fallito interrompa la procedura; l'avviso sulla posizione rimasta aperta copre il caso.
- **Registrare anche le procedure che non partono**: non hanno passi né ordini; il rifiuto torna
  all'utente come risposta.

## Conseguenze

- Una procedura dura alcuni secondi e blocca la richiesta HTTP fino all'esito.
- Su "prod" opera con fondi reali: è l'utente a lanciarla, come dice il requisito.
