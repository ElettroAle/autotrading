# ADR 0041 — Pianificazione ed esecuzione del ciclo decisionale

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.2.1, R1.2.2, R1.2.3, R1.2.4, R1.2.5 (Task T84, T86, T88, T89, T91, T93)

## Contesto

Ogni flusso attivo esegue un ciclo a ogni intervallo, giorno e notte (R1.2.1). Due cicli dello stesso flusso
non si sovrappongono mai, nemmeno tra più processi (R1.2.2). Un errore transitorio fa fallire solo il ciclo
(R1.2.3); un errore permanente mette in pausa i flussi coinvolti (R1.2.4). Una fonte che non risponde non fa
fallire il ciclo (R1.2.5). I contesti dei passi (`flows`, `sources`, `agent`, `risk`, `orders`) si sviluppano
in parallelo: il nucleo di `cycles` deve poter nascere prima di loro e senza importarli.

## Decisione

- **Pianificazione** in `CycleSchedule(anchor, interval)` nel domain: l'àncora è l'istante di avvio o di
  ripresa; l'istante previsto dovuto è l'ultimo `anchor + k·interval` non successivo a ora; il prossimo è il
  primo strettamente successivo. Un ciclo è puntuale se parte entro 60 secondi dall'istante previsto,
  altrimenti si registra il ritardo in secondi interi.
- **Esecutore**: `RunDueCyclesUseCase` è chiamato di continuo dal worker; per ogni flusso attivo lancia il
  ciclo dell'istante previsto dovuto attraverso `CycleLauncherPort`, un compito indipendente per flusso. Dopo
  un'assenza dell'esecutore si esegue solo l'ultimo istante dovuto, non l'arretrato.
- **Unicità e sovrapposizione**, due guardie distinte:
  - `CycleRepositoryPort.claim(flusso, istante previsto)`: un istante previsto si prende una sola volta; nella
    versione reale è un vincolo di unicità su (flusso, istante previsto). Così due esecutori non avviano lo
    stesso ciclo e le chiamate ripetute dell'esecutore non lo rilanciano.
  - `FlowLockPort.hold(flusso)`: esclusione non bloccante per flusso tra processi; nella versione reale è un
    advisory lock di PostgreSQL di sessione (`pg_try_advisory_lock`) sulla chiave del flusso, rilasciato a
    fine ciclo o alla caduta della connessione. Se il lock è preso, l'istante previsto si registra come
    saltato e il successivo resta al proprio istante.
- **Passi** nell'ordine del requisito, ognuno dietro una porta propria di `cycles`
  (`FlowStatePort`, `SourcePort`, `ContextPort`, `AgentPort`, `RiskPort`, `OrderPort`); i dati che passano tra
  un passo e l'altro sono opachi (`object`) per `cycles`: li interpretano solo i contesti dietro le porte,
  collegati dal ponte di integrazione in `bootstrap.py`. Gli ordini si eseguono uno alla volta nell'ordine
  approvato dal rischio.
- **Gestione degli errori**: fail fast, nessun nuovo tentativo. Un solo gestore centrale in
  `RunCycleUseCase` cattura `AutotradingError`, registra il ciclo fallito con passo, tipo e messaggio
  originale; se l'errore è permanente (`permanent = True`, proprietà del tipo) chiama
  `FlowPausePort.pause_affected_by(flusso, errore)` con il messaggio come motivo e rilancia. Quali flussi
  condividono il conto o la chiave lo decide l'adapter della porta, che conosce flussi, conti e fornitori.
  Un'eccezione che non discende da `AutotradingError` è un difetto: non si registra e risale.
- **Fonti** in `SourceCollector`: tutte insieme in un `ThreadPoolExecutor`, con attesa massima
  `min(intervallo/4, 60 s)`. Una fonte che non risponde in tempo è assente con "nessuna risposta entro N
  secondi" e non si attende (l'executor si chiude senza aspettarla); una fonte che risponde con un errore
  tipizzato è assente con il messaggio dell'errore. Se tutte mancano il ciclo prosegue con il solo stato.

## Alternative scartate

- **Solo il lock, senza `claim`**: un secondo esecutore che arriva dopo la fine del ciclo lo rieseguirebbe.
- **Solo `claim`, senza lock**: non impedisce che il ciclo successivo parta mentre il precedente è in corso.
- **Lock bloccante**: il ciclo previsto aspetterebbe il precedente invece di essere saltato, contro R1.2.2.
- **Recupero dell'arretrato**: dopo un'assenza dell'esecutore i cicli persi deciderebbero su dati vecchi.
- **Payload tipizzati dai contesti dei passi**: `cycles` importerebbe gli altri contesti, contro la regola
  delle dipendenze, e non potrebbe nascere prima di loro.
- **Nuovi tentativi sugli errori transitori**: R1.2.3 vuole il ciclo interrotto senza tentativi.
- **Fonti in sequenza o in `asyncio`**: in sequenza i tempi si sommano; `asyncio` imporrebbe porte asincrone
  a tutto il contesto per un solo passo.

## Conseguenze

- Il ponte di integrazione collega le porte agli altri contesti: `ScheduledFlowsPort`, `FlowStatePort`,
  `FlowPausePort` (`flows`), `SourcePort` (`sources`), `ContextPort` e `AgentPort` (`agent`), `RiskPort`
  (`risk`), `OrderPort` (`orders`), più gli adapter reali di `CycleRepositoryPort` (tabella dei cicli con
  vincolo di unicità e RLS), `FlowLockPort` (advisory lock), `CycleLauncherPort` (un thread per ciclo) e
  `ClockPort`, e il ciclo del worker che chiama `RunDueCyclesUseCase`.
- Gli scenari di R1.2.4 sull'ampiezza della pausa (tutti i flussi del conto, i flussi della chiave) restano
  `@wip` fino al ponte: con le porte finte proverebbero solo l'adapter finto.
- Una fonte abbandonata può restare in esecuzione fino al proprio timeout di rete: gli adapter delle fonti
  devono avere un timeout proprio.
