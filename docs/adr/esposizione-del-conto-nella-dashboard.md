# ADR esposizione-del-conto-nella-dashboard — Esposizione per direzione del conto nella dashboard

- Stato: accettata (26 novembre 2026)
- Requisiti: US 765 R5.5.5 (Task 769)
- Collegate: ADR 0116, ADR esposizione-massima-per-direzione-del-conto,
  ADR esposizione-degli-altri-flussi-nel-contesto-dell-agente; `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.5.5 chiede il campo del limite nella pagina del conto, con il motivo di rifiuto dell'API, e l'interruttore
dell'opzione nel modulo del flusso.

## Fattori decisionali

- Regole UI/UX del repository: campi accanto a ciò che riguardano, con ciò che ammettono scritto accanto.
- Nessuna logica di business nella dashboard (ADR 0116).

## Decisione

- Nella pagina del conto il campo «Esposizione massima per direzione (% del saldo)», vuoto ammesso, con la riga di aiuto
  e i comandi per impostarlo e toglierlo; il motivo di un rifiuto dell'API sotto il campo.
- Nel modulo del flusso la casella «Esposizione degli altri flussi del conto nel contesto dell'agente» accanto alle
  altre opzioni del contesto dell'agente, con la riga di aiuto.

## Alternative scartate

- **Limite nel modulo del flusso**: è un'impostazione del conto.

## Conseguenze

- La dashboard mostra ciò che l'API restituisce.
