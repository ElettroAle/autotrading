# ADR 0147 — Asset del flusso scelti dall'elenco degli asset negoziabili esposto dall'API

- Stato: accettata (14 novembre 2026), approvata dal proprietario
- Requisiti: Bug 262 (Task 265)
- Collegate: ADR 0131 (editor del flusso guidato dai cataloghi dell'API), R0.2.1 (rete dall'installazione), R1.1.1
  (validazione degli asset del flusso); `.claude/rules/tech-dashboard.md`; CLAUDE.md «Niente ponti tra contesti»

## Contesto e problema

Gli asset del flusso si scrivono a mano in un campo di testo: bisogna conoscere il nome esatto sull'exchange e un errore
emerge solo all'invio. L'adapter dell'exchange legge già gli asset negoziabili (non delistati) per validare il flusso,
ma l'API non li espone. La dashboard non può avere un elenco proprio (tech-dashboard.md).

## Decisione

- Nuovo `GET /assets`: gli asset negoziabili sull'exchange della rete dell'installazione, ordinati per nome. Il contesto
  `flows` dichiara nel proprio `ports.py` la porta che li elenca (con i suoi errori, exchange non raggiungibile = 503
  come gli altri errori dell'exchange); la realizza l'adapter dell'exchange nella sua cartella riusando la lettura che
  già fa per la validazione; un caso d'uso `ListTradableAssetsUseCase` la orchestra.
- Dashboard: il campo «Asset» diventa una scelta multipla con ricerca (digitando si filtra l'elenco, gli asset scelti
  appaiono come etichette rimovibili), alimentata da `GET /assets` con TanStack Query; se l'elenco non è disponibile
  il campo mostra il motivo e il modulo non si invia. La validazione resta all'API.

## Alternative scartate

- **Tendina semplice a scelta singola**: il flusso ammette più asset.
- **Elenco scritto nella dashboard**: diverge al primo asset nuovo o delistato, e copia un dato dell'exchange.
- **Suggerimenti sul campo di testo libero**: aiuta, ma lascia possibile inviare un nome sbagliato.

## Conseguenze

- Un asset nuovo o delistato sull'exchange compare o sparisce nel modulo senza cambiare la dashboard.
