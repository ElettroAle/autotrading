# ADR conti-a-riquadri — Un riquadro per conto con la sezione Riconciliazione

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 565, Task 566; F3.3 (riconciliazione)
- Collegate: `.claude/rules/tech-dashboard.md` §Pagine di impostazioni, ADR 0119
- Verifica: prova

## Contesto e problema

`features/accounts/components/accounts-list.tsx` mostra i conti in un `DataTable` di otto colonne; la colonna
Riconciliazione contiene un elenco di sei dati e tre comandi (`reconciliation-status.tsx`). Su ogni schermo la tabella
è compressa e illeggibile (schermata del proprietario, 17/11/2026).

## Fattori decisionali

- Bug 565; regole UX: stato visibile con icona e testo, stessa forma per ogni elemento, riquadri affiancati da `md`.
- Componenti condivisi: `DETAILS_GRID`/`DETAIL_VALUE` di `details-list.ts`, `NetworkBadge`, `CommandButton`.

## Decisione

- `AccountsList` rende un riquadro (`<article>`) per conto, in una griglia di una colonna su telefono e due da `lg`:
  intestazione con nome, rete e stato della riconciliazione; dati del conto (conto sull'exchange, saldo, capitale
  allocato e libero) in `DETAILS_GRID`; sezione «Riconciliazione» con i suoi dati e comandi (Ho verificato, Allarmi,
  Modifica la soglia); comandi del conto in fondo (Storico del capitale e gli altri di `account-actions.tsx`).
- Nessun cambiamento all'API.
- Prove: unit test del riquadro (dati, stato, comandi) e prova di layout a 360 e 1280 px senza scorrimento
  orizzontale.

## Alternative scartate

- Tabella con meno colonne e dettaglio a parte: un clic in più per lo stato della riconciliazione.

## Conseguenze

- I conti si leggono su telefono.
