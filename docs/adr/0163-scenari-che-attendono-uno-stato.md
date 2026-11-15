# ADR 0163 — Scenari della dashboard che attendono uno stato osservabile, mai il tempo

- Stato: proposta (15 novembre 2026)
- Requisiti: Bug 289 (Task 290)
- Collegate: ADR 0119 (rilettura con TanStack Query), ADR 0116

## Contesto e problema

In CI gli scenari R2.5.1 e R2.1.2 falliscono a turno e passano in locale. In R2.1.2 l'API finta viene fermata mentre
una lettura della pagina non è ancora finita: quella lettura fallisce e mostra un secondo avviso, e il localizzatore
generico `getByRole('alert')` va in strict mode. In R2.5.1 la tabella non ha righe entro i 5 secondi dell'attesa, e
lo scenario «Ordini ed esecuzioni per conto» impiega 12-13 secondi anche in locale.

## Fattori decisionali

- `.claude/rules/tests.md`: ogni prova si vede rossa prima di diventare verde; prove deterministiche.
- Nessuna prova disattivata, nessun timeout allungato per far passare (skill e contratto).

## Opzioni considerate

### 1. Passi che attendono uno stato osservabile e localizzatori specifici, causa della lentezza corretta

- Pro: scenari deterministici; la lentezza di R2.5.1 si corregge alla fonte.
- Contro: va trovata la causa dei 12-13 secondi.

### 2. Ripetizioni automatiche (`retries`) o timeout più lunghi

- Pro: immediato.
- Contro: nasconde il problema; vietato dalle regole sulle prove.

## Esito della decisione

Opzione 1. Prima di simulare un guasto dell'API, un passo attende che la pagina abbia finito di leggere i suoi dati
(nessuna lettura in corso, elementi della pagina visibili). Gli avvisi si cercano per testo o per nome, non con il
generico `role=alert`. La lentezza di R2.5.1 si misura, se ne trova la causa (attese a tempo, letture ripetute,
paginazione dell'API finta) e si corregge dove nasce. Una prova di stabilità ripete in locale gli scenari coinvolti
sotto carico (lavoratori paralleli come in CI) e li vede passare tutti.

Verifica: revisione.

### Conseguenze

- Un nuovo passo che simula un guasto attende lo stato della pagina, non un tempo.
