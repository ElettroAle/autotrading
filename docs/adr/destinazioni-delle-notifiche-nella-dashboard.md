# ADR destinazioni-delle-notifiche-nella-dashboard — Ogni notifica dichiara dove porta nella dashboard

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.6, Task 587; R1.8.1, R3.5.2
- Collegate: ADR canali-delle-notifiche-come-insieme, ADR 0117 (dashboard su `/dashboard` dello stesso nome HTTPS di
  `api`), memoria del proprietario «adapter configurabili, mai ricavati dal nome dell'installazione»
- Verifica: prova

## Contesto e problema

Una notifica (`domain/notifications/notification.py`) porta solo nomi (flusso o conto come `subject`), nessun id: non
può dire quale pagina aprire. Il backend non conosce l'indirizzo della dashboard. Il proprietario (17/11/2026) vuole
dalla notifica il flusso, l'operazione (scheda Posizioni o Posizioni chiuse con la posizione evidenziata) e, per gli
eventi del conto, la pagina Allarmi del conto.

## Fattori decisionali

- R3.5.6 e le decisioni del proprietario (17/11/2026) scritte nella User Story.
- La dashboard è un sistema integrato a sé (container proprio, ADR 0116): le sue rotte e il suo indirizzo stanno in una
  sola cartella adapter, non in `telegram/` e `smtp/` insieme.
- Configurazione per adapter: l'indirizzo è un'impostazione esplicita dell'installazione, mai derivata dal nome.
- Domain e application non conoscono indirizzi né rotte.

## Decisione

- Domain: `NotificationTarget` (value object) con il genere — `FLOW`, `OPEN_POSITION`, `CLOSED_POSITION`,
  `ACCOUNT_ALARMS` — e gli identificativi che servono (id del flusso; asset; istante di chiusura; id del conto).
  `Notification` porta `targets: tuple[NotificationTarget, ...]`; le fabbriche delle notifiche di flusso ricevono l'id del
  flusso, quelle delle posizioni anche asset e, se chiusa, l'istante di chiusura, quelle del conto l'id del conto. Al
  posto della ricerca del flusso per nome in `NotifyUseCase` si usa l'id.
- Application: porta `NotificationLinkPort.link(target) -> NotificationLink | None` (`label`, `url`) in
  `application/notifications/ports.py`. `NotifyUseCase` aggiunge i link al messaggio di ogni canale (payload dell'outbox
  `links: [{label, url}]`). Etichette: «Apri flusso», «Apri operazione», «Apri allarmi».
- Adapter `adapters/outbound/dashboard/` (nuova cartella di tecnologia, nessuna libreria esterna):
  `DashboardNotificationLinkAdapter` traduce il genere nella rotta (`/flows/{id}`, `/flows/{id}/positions?asset=…`,
  `/flows/{id}/closed-positions?asset=…&closed_at=…`, `/accounts/{id}/alarms`) e la unisce all'indirizzo in
  `_DashboardSettings` (`DASHBOARD_URL`, facoltativo: senza indirizzo `link` restituisce `None` e le notifiche partono
  senza link). `composition.py` espone `dashboard_adapters(source)`; contratto di indipendenza in import-linter.
- Deploy: `DASHBOARD_URL` del worker nell'ambiente dell'installazione (variabile dell'ambiente GitHub, non segreto),
  impostata per dev con l'indirizzo HTTPS di Tailscale seguito da `/dashboard`.
- Prove: scenari R3.5.6 sui casi d'uso con un finto della porta; unit test dell'adapter (rotte, indirizzo assente);
  prova di architettura che nessuna rotta della dashboard compare fuori da `adapters/outbound/dashboard/`.

## Alternative scartate

- Rotte e indirizzo dentro gli adapter Telegram e SMTP: due copie della stessa mappa.
- Rotte in application: un dettaglio della dashboard nel nucleo.

## Conseguenze

- Un canale nuovo riceve i link già pronti nel payload.
