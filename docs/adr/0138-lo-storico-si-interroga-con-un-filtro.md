# ADR 0138 — Lo storico si interroga con un filtro del dominio e pagine di 50 per chiave

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.5.1 (Task T2.5.1.1)
- Collegate: RF-20.04; R1.7.3 (cicli), R1.6.2 (posizioni chiuse), ADR delle operazioni con paginazione per chiave
  (E1), CLAUDE.md «Multi-tenancy» (RLS), docs/architecture.md §3

## Contesto e problema

Tre storici (cicli, posizioni chiuse, ordini con esecuzioni) si filtrano per flusso, conto, periodo, asset e
versione della configurazione in combinazione; la versione vale per un solo flusso; risultati dal più recente a
pagine di 50, solo dati dell'utente.

## Decisione

- Value object `HistoryFilter` nel dominio `flows`: flusso, conto, periodo (`StatisticsPeriod` di ADR 0122),
  asset, versione; un invariante rifiuta la versione senza un flusso (errore del dominio, 400).
- Tre casi d'uso del contesto `flows` (`QueryCycleHistoryUseCase`, `QueryClosedPositionHistoryUseCase`,
  `QueryOrderHistoryUseCase`) su porte del contesto realizzate in `adapters/outbound/sqlalchemy/`, con la
  paginazione per chiave (istante, id) già usata dalle operazioni e RLS del tenant.
- Indici composti per tenant, flusso e istante dove le interrogazioni li richiedono, con una migrazione Alembic.
- API: `GET /history/cycles`, `GET /history/closed-positions`, `GET /history/orders` con i filtri come parametri e
  il cursore della pagina successiva.

## Alternative scartate

- **Paginazione per numero di pagina (offset)**: più semplice, ma lenta e instabile mentre arrivano cicli nuovi.
- **Un solo endpoint con il tipo di storico come parametro**: meno rotte, ma risposte di forma diversa sotto lo
  stesso schema.

## Conseguenze

- La pagina dello storico (T2.5.1.2) usa solo questi tre endpoint.
