# ADR 0070 — Ogni chiusura notificata una volta, con il PnL dell'exchange

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.8.2, R1.7.2, Bug 161
- Collegate: ADR 0047 (storico delle posizioni chiuse), 0055 (stop), 0054 (rimozione del conto), 0056 (notifiche e
  chiusure registrate dal ciclo), 0061 (chiusura manuale)

## Contesto

R1.8.2 chiede la notifica di ogni chiusura di una posizione di un flusso. Solo due strade notificavano: la chiusura
decisa dall'agente e quella trovata fuori dalla piattaforma dalla riconciliazione. Stop, rimozione del conto e
comando manuale scrivevano nello storico senza notificare: girano nell'API, mentre il bot Telegram vive solo nel
`worker` (ADR 0035).

Il PnL inoltre era doppio: la notifica riportava il `closedPnl` dell'exchange, lo storico lo ricalcolava come margine
× leva × variazione del prezzo (ADR 0047). I due coincidono solo per una posizione aperta in un colpo solo dal flusso.

## Decisione

- **Il PnL è quello dell'exchange.** `ClosingFill` e `ClosedPosition` portano `realized_pnl`, il PnL che l'exchange
  ha riportato per la chiusura; `ClosedPosition.pnl` è quello, e solo in sua assenza il ricalcolo di ADR 0047.
  Tutte le chiusure lo passano: esito dell'ordine dell'agente, esito della chiusura dello stop e del comando manuale,
  `closedPnl` della chiusura fuori dalla piattaforma. Nuova colonna `closed_positions.realized_pnl` (migrazione
  0016), vuota per le righe già scritte.
- **Una chiusura si notifica quando entra nello storico.** `NotifiedClosedPositions` in `bootstrap.py` avvolge la
  `ClosedPositionRepositoryPort`: dopo l'inserimento notifica il flusso, l'asset e lo stesso `pnl` che lo storico
  conserva. Avvolge lo storico ovunque si scriva:
  - nel `worker`, per la chiusura dell'agente e per la chiusura fuori dalla piattaforma, con `NotifyUseCase`;
  - nell'API, per lo stop, la rimozione del conto e il comando manuale, con `HttpxNotificationAdapter`.
- **L'API consegna la notifica al `worker`**: nuova rotta interna `POST /tenants/{tenant_id}/notifications` con
  soggetto ed evento, protetta dal token dell'installazione come le altre (ADR 0021); il `worker` la passa a
  `NotifyUseCase`, che la manda solo alla chat collegata al tenant. Un `worker` che non risponde si registra nel log
  e non fa fallire lo stop o la chiusura, che sull'exchange è già avvenuta (R1.8.2).
- **Le notifiche dirette restano solo per le chiusure senza storico**: una chiusura dell'agente su una posizione che
  il flusso non ha mai aperto, e una chiusura fuori senza apertura del flusso o con una perdita che non implica un
  prezzo. Si notificano una volta, dal ponte che non ha potuto scriverle. La riconciliazione non notifica più le
  chiusure fuori: lo fa lo storico.

## Alternative scartate

- **Bot Telegram anche nell'API**: il token del bot andrebbe montato in un secondo container, e i due processi
  leggerebbero gli aggiornamenti dello stesso bot in concorrenza.
- **Notificare nel `worker` dalla rotta di chiusura**: la rotta non conosce il flusso né il motivo; portarli nel
  contratto HTTP lega la chiusura di `orders` ai flussi (ADR 0061).
- **Notifiche nei casi d'uso di `flows`** (stop, comando manuale): ogni nuova strada di chiusura dovrebbe ricordarsi
  di notificare; il punto unico è lo storico.
- **Tenere il ricalcolo nello storico e correggere la notifica**: il ricalcolo usa l'ultima apertura del flusso e
  sbaglia appena la posizione è stata aumentata o chiusa a pezzi; il `closedPnl` è il risultato vero.

## Conseguenze

- Ogni chiusura che entra nello storico arriva sulla chat una volta, con lo stesso PnL che l'utente legge nello
  storico.
- Una chiusura dell'API che il `worker` non riceve resta nello storico senza notifica, con un avviso nel log.
- Le righe scritte prima di 0016 mostrano ancora il PnL ricalcolato.
- Una posizione aperta a mano su un asset del flusso e chiusa dallo stop o dal comando manuale non entra nello
  storico e non si notifica (ADR 0055, 0061).
