# ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte — Riconciliazione periodica dei conti con posizioni aperte

- Stato: accettata (28 novembre 2026, decisione del proprietario)
- Requisiti: Bug 778 (Task 779); R1.6.2, R3.1.2
- Collegate: sostituisce ADR 0063 nella sola regola su quando si scrive il registro (resto di ADR 0063 invariato);
  ADR 0042 (esclusione dei cicli con advisory lock), ADR 0045 (riconciliazione), ADR chiusure-per-protezione-nello-storico,
  ADR sorveglianza-del-prezzo-per-lo-stop-che-segue (controllo periodico del worker), ADR
  intervallo-di-riconciliazione-del-conto; `.claude/rules/context-flows.md`, `.claude/rules/tech-apscheduler.md`
- Verifica: prova

## Contesto e problema

Registro e storico si aggiornano solo con la riconciliazione del conto all'inizio e alla fine di ogni ciclo (ADR 0063).
Uno stop loss, un take profit, una liquidazione o una chiusura esterna avvenuti tra due cicli restano fuori dallo
storico fino al ciclo successivo, anche 24 ore su un flusso giornaliero. Nel frattempo la posizione è sparita dallo
stato del flusso, ma i suoi soldi non contano il risultato. Rilevato il 27 novembre 2026 sui flussi di studio.

## Fattori decisionali

- Decisione del proprietario (28 novembre 2026): un controllo periodico riconcilia i soli conti con posizioni dei flussi
  aperte, per non consumare il limite di richieste dell'exchange. L'intervallo si configura sul conto, predefinito
  5 minuti.
- ADR 0063: il registro si scrive solo con `RecordAccountExecutionsUseCase`, leggendo dall'exchange solo ciò che è
  nuovo. Resta valido: cambia solo quando si scrive.
- ADR 0042: due cicli dello stesso flusso non sono mai in corso insieme, e un ciclo previsto mentre il flusso è tenuto
  viene saltato. La riconciliazione periodica non deve quindi tenere i flussi: un ciclo giornaliero saltato perderebbe
  un giorno.
- Nessuna regola per un exchange: vale per Hyperliquid e per l'exchange simulato.

## Decisione

- **Caso d'uso.** `ReconcileOpenAccountsUseCase` in `application/flows`, per il tenant. Per ogni conto dei flussi in uso:
  - legge l'ultima lettura salvata (`ReconciliationRepositoryPort.last_reading`), senza chiamare l'exchange;
  - salta il conto se nessun flusso aveva posizioni aperte in quella lettura;
  - salta il conto se dall'istante di quella lettura non è passato l'intervallo del conto (ADR
    intervallo-di-riconciliazione-del-conto);
  - prende senza attesa l'esclusione della riconciliazione del conto, un advisory lock PostgreSQL per conto distinto
    da quello dei cicli. Se un'altra riconciliazione dello stesso conto è in corso salta il conto. Non prende
    l'esclusione dei flussi (`FlowLockPort`): un ciclo previsto in quell'istante deve partire, non essere saltato;
  - poi riconcilia il conto con `ReconcileAccountUseCase`, che già registra esecuzioni, chiusure per protezione e
    chiusure fuori dalla piattaforma, e avvisa dei casi nuovi come nel ciclo.

  La regola «posizioni aperte e intervallo trascorso» sta nel domain.
- **Esclusione della riconciliazione.** Ogni riconciliazione di un conto, del ciclo o periodica, tiene l'esclusione del
  conto per la sua durata: quella del ciclo la attende, quella periodica la prova senza attesa. Due riconciliazioni dello
  stesso conto non scrivono mai il registro insieme. L'esclusione è una porta di `flows` realizzata nella cartella
  `sqlalchemy`, con una chiave distinta da quella dei cicli.
- **Errori.** Un exchange non disponibile lascia il conto com'è: si registra un avviso e il controllo successivo ritenta.
  Nessuna pausa dei flussi da questo controllo.
- **Pianificazione.** Un controllo periodico del worker ogni minuto, per ogni tenant, con la base condivisa dei
  controlli periodici della cartella `apscheduler` (stessa forma della sorveglianza dello stop che segue). L'intervallo
  di ogni conto decide se leggerlo.
- **Regola del contesto.** In `.claude/rules/context-flows.md` la frase «dalla riconciliazione del conto all'inizio e
  alla fine di ogni ciclo» diventa «dalla riconciliazione del conto all'inizio e alla fine di ogni ciclo e dal controllo
  periodico dei conti con posizioni aperte (ADR riconciliazione-periodica-dei-conti-con-posizioni-aperte)».

## Alternative scartate

- **Riconciliare solo dopo una chiusura del simulato**: lascia il ritardo su Hyperliquid.
- **Leggere tutti i conti a ogni controllo**: consuma il limite di richieste anche senza posizioni.
- **Tenere l'esclusione dei flussi del conto** (`FlowLockPort`): un ciclo previsto in quell'istante verrebbe saltato.
- **Aspettare il ciclo in corso**: bloccherebbe il controllo per la durata del ciclo, che riconcilia comunque.

## Conseguenze

- Una chiusura tra due cicli entra nello storico entro l'intervallo del conto, più al massimo un minuto.
- Un conto con posizioni aperte riceve una lettura dell'exchange per intervallo in più rispetto ai cicli.
