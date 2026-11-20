# ADR indice-delle-previsioni-in-attesa-e-patrimonio-con-limite-superiore — Indice parziale delle previsioni in attesa e query del patrimonio sempre con limite superiore

- Stato: proposta (20 novembre 2026)
- Requisiti: Bug 635 (Task 640)
- Collegate: ADR 0063; `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/context-flows.md`
- Verifica: prova

## Contesto e problema

Misure su dev del 20 novembre 2026 (`pg_stat_user_tables`, `EXPLAIN ANALYZE` con RLS):
- `SqlAlchemyForecastRepositoryAdapter.expired_without_actual` (`actual_price IS NULL AND now >= made_at + horizon`),
  chiamata dal giro del worker ogni 5 secondi, legge tutta `forecasts` con un seq scan: 83.472 scansioni e 71,8 milioni
  di righe lette dal 15 novembre, mentre le righe senza prezzo effettivo sono 15. La tabella cresce di circa 370 righe
  al giorno.
- Le query di `equity_snapshots` senza limite superiore (periodo «tutto», `peak_query` della guardia della perdita)
  non potano le 51 partizioni in pianificazione: 50–59 ms di pianificazione a connessione fredda, 2–4,5 ms di
  esecuzione contro 0,2 ms con entrambi i limiti.

## Fattori decisionali

- Decisione del proprietario (20 novembre 2026, in chat, punto 5 dell'analisi del Bug 635): entrambe le correzioni.
- `tech-sqlalchemy.md`: ogni modifica di schema passa da una migrazione Alembic.
- CLAUDE.md: l'istante corrente viene solo dall'orologio di sistema; il domain non conosce l'ORM.

## Decisione

- Migrazione Alembic con `CREATE INDEX forecasts_awaiting_actual ON forecasts (tenant_id, made_at) WHERE
  actual_price IS NULL`; la query resta la stessa.
- Le letture del patrimonio hanno sempre un limite superiore: una finestra senza fine (periodo «tutto», periodo
  personalizzato aperto) termina all'istante della richiesta che il caso d'uso riceve dall'orologio, comprese le
  istantanee di quell'istante; `loss_references` riceve anche l'istante corrente e `peak_query` lo usa come limite
  superiore. Gli esiti non cambiano: non esistono istantanee future.
- Le partizioni pre-create e il pool di connessioni non cambiano.

## Alternative scartate

- Limite superiore con `now()` di PostgreSQL: funzione stabile, la potatura avverrebbe solo in esecuzione.
- Meno partizioni pre-create: riduce il problema senza toglierlo e cambia la manutenzione delle partizioni.

## Conseguenze

- Il giro delle previsioni legge le sole righe in attesa, a costo costante.
- Le query del patrimonio pianificano su una o poche partizioni.
