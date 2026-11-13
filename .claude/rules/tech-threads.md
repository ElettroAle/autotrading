---
paths:
  - "src/autotrading/adapters/outbound/threads/**"
  - "tests/unit/adapters/threads/**"
---

# Adapter in uscita: thread del processo

- Il sistema integrato sono i thread del sistema operativo, che domain, application e `bootstrap.py` non possono
  usare (`threading`, `concurrent` sono librerie standard tecniche): qui, e solo qui, si avviano thread e si
  condivide stato tra thread. Nessuna libreria esterna.
- `ThreadPoolConcurrentCallsAdapter` esegue le chiamate in parallelo e attende al più i secondi dati (R1.2.5): una
  chiamata ancora in corso si abbandona, mai si attende; l'esito è risposta, errore del progetto o assenza di risposta.
- `ThreadsPlannedFlowsAdapter` ricorda i tenant dei flussi pianificati tra un giro e l'altro del `worker`, con un lock.
- Nei test nessuna attesa a tempo: si sincronizza con eventi o si controlla l'esito.
