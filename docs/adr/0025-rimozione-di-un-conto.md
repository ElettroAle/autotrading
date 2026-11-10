# ADR 0025 — Rimozione di un conto: credenziali cancellate, riga conservata per lo storico

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.2.5

## Contesto

R0.2.5 chiede che un utente rimuova un conto che non usa più. La rimozione cancella le credenziali
ma lascia consultabile lo storico delle operazioni del conto, e non tocca le posizioni sull'exchange.
Con posizioni aperte la rimozione chiede una conferma esplicita: senza conferma resta sospesa con il
motivo "il conto ha posizioni aperte che resteranno sull'exchange senza gestione".

Lo storico del conto sono gli ordini (tabella `orders`, ADR 0022) e le procedure di verifica
(`verification_runs`, ADR 0024). Entrambe le tabelle hanno una chiave esterna composta verso
`accounts(id, tenant_id)`. Le posizioni si leggono solo nel `worker` (ADR 0021).

## Decisione

- **Rimozione logica.** La riga del conto resta, con `removed_at` impostato; chiave e testo cifrato
  delle credenziali diventano `NULL` nello stesso `UPDATE`. Le chiavi esterne di ordini e procedure
  restano valide e lo storico resta leggibile.
- **Un conto rimosso non esiste più per l'applicazione.** `list`, `get` e `name_in_use` del repository
  filtrano `removed_at IS NULL`: un conto rimosso risponde "non trovato" come un conto di un altro
  tenant (R0.1.3). Il nome torna libero: il vincolo di unicità diventa un indice unico parziale
  `WHERE removed_at IS NULL` (migrazione 0006). Il tipo `Account` del domain non cambia: le
  credenziali di un conto caricato ci sono sempre.
- **`RemoveAccountUseCase` (API).** Riceve conto e conferma.
  - Senza conferma legge lo stato dal `worker` (porta `AccountStatePort`, ADR 0021). Con posizioni
    aperte solleva `AccountRemovalNeedsConfirmationError` (409) e non rimuove nulla.
  - Con conferma non legge lo stato: la conferma accetta che le posizioni restino sull'exchange, e
    funziona anche con credenziali già revocate o exchange non raggiungibile.
  - Senza conferma, se lo stato non si legge, valgono gli errori della lettura (422 o 503): la
    piattaforma non sa se ci sono posizioni, e l'utente può confermare.
  - La rimozione si registra nel log delle operazioni con il solo identificativo del conto (R0.2.3).
- **Porta**: `AccountRepositoryPort.remove(account_id)`. Solleva `AccountNotFoundError` se non rimuove
  alcuna riga (conto inesistente, già rimosso o di un altro tenant).
- **API**: `DELETE /accounts/{conto}?confirmed=true|false` (predefinito `false`), 204 a rimozione fatta.

## Alternative scartate

- **Cancellazione della riga con `ON DELETE SET NULL` sugli ordini**: lo storico perderebbe il
  legame con il conto e con il tenant, che la chiave esterna composta garantisce.
- **Tabella separata dei conti rimossi**: sposta righe referenziate da altre tabelle senza un vantaggio.
- **Credenziali opzionali nel tipo `Account`**: ogni uso delle credenziali dovrebbe gestire un caso che,
  per un conto non rimosso, non esiste.
- **Lettura delle posizioni anche con conferma**: impedirebbe la rimozione di un conto con credenziali
  revocate, proprio il caso in cui l'utente vuole liberarsene.

## Conseguenze

- Ogni query futura su `accounts` deve escludere i conti rimossi: il repository è l'unico punto che le
  scrive.
- Lo storico resta in database anche per un conto rimosso; una sua consultazione dall'API arriverà con
  i requisiti che la chiedono.
