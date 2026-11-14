# ADR 0136 — Pagina della classifica ordinabile con il periodo condiviso

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.4.2 (Task T2.4.2.2)
- Collegate: ADR 0116, ADR 0119, ADR 0123 (selettore del periodo nella query string), ADR 0128 (`data-table`),
  ADR 0135

## Contesto e problema

La pagina mostra la classifica del periodo scelto, ordinabile per qualsiasi colonna, con rendimento decrescente
come predefinito, e da lì l'utente sceglie i flussi da sovrapporre (R2.4.3).

## Decisione

- Funzionalità `ranking`: query su `GET /flows/ranking` con il periodo del selettore condiviso (ADR 0123).
- Ordinamento nel browser sulle righe ricevute, con colonna e verso nella query string; confronto numerico sui
  valori decimali dell'API, «non disponibile» sempre in fondo.
- `data-table` (ADR 0128) esteso con intestazioni ordinabili accessibili (`aria-sort`).
- Caselle di scelta dei flussi (al più 5) che portano alla vista delle curve sovrapposte con i flussi scelti nella
  query string.

## Alternative scartate

- **TanStack Table**: ordinamento pronto, ma una dipendenza in più per una sola tabella ordinabile.

## Conseguenze

- Classifica e curve sovrapposte condividono periodo e flussi scelti tramite l'URL.
