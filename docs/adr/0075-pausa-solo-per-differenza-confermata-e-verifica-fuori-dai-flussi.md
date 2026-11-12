# ADR 0075 — Pausa solo per una differenza confermata e procedura di verifica fuori dai flussi

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.6.2, R0.4.1; Bug 165
- Collegate: ADR 0064 (blocco su posizione diversa), ADR 0063 (registro delle operazioni), ADR 0024 (procedura di
  verifica nel worker)

## Contesto

L'ADR 0064 mette in pausa il flusso quando, all'inizio del ciclo, la posizione del conto su un suo asset è diversa da
quella attesa dal registro. Due casi producevano una pausa per una differenza che non c'è:

- **Esecuzione pubblicata in ritardo**: il ciclo legge prima le esecuzioni nuove e poi le posizioni. Un'esecuzione
  che l'exchange pubblica tra le due letture compare già nella posizione ma non ancora nel registro. L'ADR 0064 ne
  accettava il costo; il flusso però resta fermo finché l'utente non lo riprende, per una differenza che il ciclo
  successivo non vedrebbe più.
- **Procedura di verifica (R0.4.1)**: apre e chiude BTC sul conto. Il registro attribuiva le sue esecuzioni al flusso
  che ha BTC tra i suoi asset, come se fossero chiusure esterne o ordini del flusso, e un ciclo che cade a metà
  procedura vede una posizione BTC che il flusso non ha aperto.

## Decisione

- **Riconciliazione ripetuta prima della pausa**: in `FlowStateFromFlows`, quando il confronto trova una
  differenza, il conto si riconcilia un'altra volta (`ReconcileAccountUseCase`, che registra le esecuzioni nuove con
  `RecordAccountExecutionsUseCase`) e il confronto si ripete sullo stato riletto. `FlowPositionMismatchError` si
  solleva solo se la differenza resta. Se la seconda riconciliazione non riesce, il ciclo fallisce con
  `FlowExchangeUnavailableError` (transitorio): il flusso non va in pausa e il ciclo successivo confronta di nuovo.
- **Ordini della procedura fuori dai flussi**: la porta degli ordini della piattaforma restituisce per ogni ordine il
  flusso che l'ha inviato e se l'ha inviato la procedura di verifica (`PlatformOrder`, dall'origine dell'ordine). Nel
  registro un'esecuzione di un ordine della procedura è sempre non attribuita, anche su un asset di un flusso: non
  diventa una chiusura esterna del flusso né entra nei suoi totali.
- **Procedura rifiutata sull'asset di un flusso**: la procedura non parte su un conto in cui un flusso attivo o in
  pausa ha BTC tra i suoi asset. Il domain solleva `AssetOfFlowError` (sottoclasse di `VerificationNotStartedError`,
  409) con il motivo "BTC è un asset del flusso alfa", prima di ogni lettura dell'exchange e di ogni ordine.
  `AccountReadingPort.flow_on(account_id, asset)` dà il nome del flusso; il ponte `AccountReadingFromAccounts` in
  `bootstrap.py` lo legge dal repository dei flussi del tenant. Un flusso fermo non esegue cicli: non blocca la
  procedura.

## Alternative scartate

- **Attendere qualche secondo prima di rileggere**: allunga ogni ciclo con una differenza vera senza garantire che
  l'exchange abbia pubblicato; la seconda riconciliazione legge quello che c'è.
- **Mettere in pausa al secondo ciclo consecutivo con la differenza**: lascia operare per un intero ciclo un flusso
  con una posizione incerta, che è ciò che l'ADR 0064 vieta.
- **Attribuire al flusso le esecuzioni della procedura e compensarle**: la procedura non è del flusso; il suo PnL e
  le sue fee entrerebbero nei numeri dell'agente e del rischio.
- **Lasciare partire la procedura e sospendere i cicli del flusso durante l'esecuzione**: serve un lock tra worker e
  ciclo; il rifiuto è più semplice e dice all'utente cosa fare (fermare il flusso).

## Conseguenze

- Una differenza vera costa una lettura in più delle esecuzioni prima della pausa.
- Un'esecuzione pubblicata più tardi anche della seconda lettura ferma ancora il flusso: resta il caso dell'ADR 0064,
  molto più raro.
- Per verificare l'esecuzione su un conto con un flusso su BTC l'utente deve prima fermare il flusso.
- Le esecuzioni della procedura restano nel registro come non attribuite ma ordini della piattaforma: la
  riconciliazione non le segnala come movimenti non attribuibili (R1.6.2), perché la procedura le registra già.
