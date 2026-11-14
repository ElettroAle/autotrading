# ADR 0129 — Elenco e dettaglio dei cicli, con i testi del modello mai interpretati come HTML

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.2.7 (Task T2.2.7.1)
- Collegate: ADR 0116, ADR 0119, ADR 0128 (`data-table`); R1.7.3 (`GET /flows/{id}/cycles`,
  `GET /flows/{id}/cycles/{planned_at}`)

## Contesto e problema

Il dettaglio di un ciclo contiene testi lunghi (ragionamento, contesto, risposta del modello), fonti, controllo
del rischio, ordini ed eventuale errore; l'elenco è paginato dall'API.

## Decisione

- Funzionalità `cycles`: elenco paginato con `data-table`; dettaglio su una rotta propria
  `/flows/:flowId/cycles/:plannedAt`, così un ciclo ha un link condivisibile.
- Sezioni del dettaglio richiudibili; i testi del modello e delle fonti come testo preformattato, mai come HTML,
  per non eseguire contenuti arrivati dall'esterno.
- Un ciclo fallito mostra passo, tipo e messaggio dell'errore come li dà l'API.

## Alternative scartate

- **Dettaglio in una finestra sopra l'elenco**: niente cambio di pagina, ma nessun link al singolo ciclo.
- **Rendering Markdown della risposta del modello**: più leggibile, ma apre una superficie XSS.

## Conseguenze

- Nessun endpoint nuovo.
