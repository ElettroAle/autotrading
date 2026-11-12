# ADR 0055 — Stop di un flusso

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.1.5 (Task T1.1.5.1), R1.7.2 per i motivi "stop del flusso" e "rimozione del conto"

## Contesto

Fermare un flusso attivo o in pausa chiude le sue posizioni aperte e lo porta nello stato fermo; un ciclo in corso
finisce prima della chiusura, così non apre una posizione dopo di essa; una chiusura rifiutata dall'exchange lascia
il flusso fermo e la posizione indicata all'utente (R1.1.5). Le posizioni le chiude solo il `worker`, l'unico
servizio con la chiave (ADR 0007, ADR 0023). Ogni posizione chiusa entra nello storico col suo motivo (R1.7.2,
ADR 0047).

## Decisione

- **Domain**: il comando `FlowCommand.STOP` parte da attivo o in pausa e porta a fermo; `starts_from` diventa un
  insieme di stati. `StopOutcome` porta il flusso fermato e le `PositionLeftOpen` (asset, motivo del rifiuto).
- **Caso d'uso** `StopFlowUseCase(flows, StopPorts)`, nell'ordine: cambia lo stato (nessun ciclo nuovo parte),
  attende la fine del ciclo in corso, chiude la posizione di ogni asset del flusso. `StopFlowCommand` porta
  l'utente, a cui si attribuisce ogni ordine di chiusura (R0.3.2), e il motivo (`FLOW_STOP` di norma,
  `ACCOUNT_REMOVAL` dalla rimozione del conto, ADR 0054).
- **Attesa del ciclo**: `RunningCyclePort.wait_until_finished`; l'adapter PostgreSQL prende e rilascia subito
  `pg_advisory_lock` con chiave = i primi 8 byte dell'UUID del flusso come bigint con segno (`lock_key` di
  `scheduling.py`), la stessa che `SqlAlchemyFlowLockAdapter` tiene per tutto il ciclo (ADR 0042).
- **Chiusura**: `FlowPositionsPort.close` restituisce `PositionClosing` con il fill (prezzo medio, istante,
  commissione) o il motivo del rifiuto, o niente se sull'asset non c'è posizione. Il ponte in `bootstrap.py` usa
  `PositionClosingPort` di `orders`; un esito senza prezzo, istante o commissione (non confermato in tempo) conta
  come posizione forse ancora aperta.
- **Storico**: per ogni posizione chiusa `FlowOpeningsPort.last_opening` legge l'ultima apertura eseguita del
  flusso su quell'asset dagli ordini registrati (ADR 0050); la posizione si salva con commissioni di apertura e
  chiusura e il motivo del comando. Una posizione senza apertura del flusso (aperta a mano sul suo asset) si
  chiude senza storico, con un avviso nel log.
- **API**: `POST /flows/{id}/stop` risponde il flusso e le posizioni rimaste aperte.

## Alternative scartate

- **Chiusura prima del cambio di stato**: un ciclo potrebbe partire tra la chiusura e lo stop e riaprire.
- **Flag "in corso" nella tabella dei cicli**: un `worker` caduto a metà lascerebbe il flag acceso per sempre;
  l'advisory lock si libera con la connessione.
- **Fallire lo stop a una chiusura rifiutata**: R1.1.5 vuole il flusso fermo comunque.
- **Ricostruire l'apertura dalla posizione dell'exchange**: l'exchange non conosce né il ciclo né le commissioni
  di apertura.

## Conseguenze

- La chiave del lock resta una sola (`lock_key`): se l'esecutore dei cicli la cambia, l'attesa dello stop ritorna
  subito.
- Lo schema "Motivi di chiusura" di R1.7.2 è attivo per stop e rimozione del conto; chiusura manuale e liquidazione
  restano `@wip` fino a R1.6.1.
