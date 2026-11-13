---
paths:
  - "src/autotrading/adapters/outbound/worker/**"
  - "tests/unit/adapters/worker/**"
---

# Adapter in uscita: API interna del worker

- Client dell'API interna del `worker` usati dall'`api` (ADR 0021), raggiunta con `httpx`, libreria di
  trasporto condivisa. Il contratto lato server è `adapters/inbound/api/worker.py`.
- Ogni chiamata porta il token di servizio come `Authorization: Bearer`, letto da file montato in sola
  lettura; ha un timeout esplicito dichiarato nel modulo.
- Gli adapter (`WorkerAccountStateAdapter`, `WorkerAccountActivityAdapter`, `WorkerPositionClosingAdapter`,
  `WorkerVerificationAdapter`, `WorkerBotIdentityAdapter`, `WorkerNotificationAdapter`) sono legati al
  tenant della richiesta quando il dato è del tenant e realizzano porte dei contesti consumatori.
- Il worker non raggiungibile o uno stato inatteso si traduce nell'errore del contratto della porta; una
  notifica non consegnata si registra e non fa fallire il chiamante (R1.8.2).
- Il token non compare in log, errori o repr. Nessun import da altre cartelle di adapter.
