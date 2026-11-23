# ADR intervallo-delle-liste-fissato-alla-scelta-del-periodo — Intervallo delle liste fissato alla scelta del periodo

- Stato: proposta (22 novembre 2026)
- Requisiti: Bug 716, Task 717
- Collegate: ADR periodo-al-minuto, ADR periodi-brevi-nel-selettore-condiviso, ADR 0119 (rilettura ogni 30 secondi),
  ADR test-della-dashboard-instabili-corretti-alla-radice, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

Le liste della dashboard filtrate su un periodo recente calcolano l'inizio del periodo dal minuto corrente a ogni render
(`listIntervalOf(period, new Date())`). Quell'inizio entra nella chiave della query di TanStack Query. Quando cambia il
minuto la chiave cambia: parte una lettura nuova dalla prima pagina, e le pagine già lette con «Altri» spariscono. Lo
stesso schema è in:

- unattributable-movements, alerts-list e cycles-list;
- account-capital-changes e flow-capital-changes;
- closed-positions ed equity-curve.

## Fattori decisionali

- ADR periodo-al-minuto: le liste chiedono all'API gli istanti al minuto.
- ADR 0119: i dati della pagina si rileggono ogni 30 secondi con la stessa query; una rilettura non deve cambiare la
  chiave.
- Codice condiviso in `src/components/ui/period-selector`, nessuna logica duplicata per funzionalità (bulletproof-react).

## Decisione

- L'istante da cui si calcola l'intervallo si fissa quando la lista riceve il periodo: all'apertura della pagina e a
  ogni cambio del periodo scelto. Resta lo stesso per tutti i render e per le riletture finché il periodo non cambia.
- Un hook condiviso accanto a `listIntervalOf` in `src/components/ui/period-selector/use-period.ts` (es.
  `useListInterval(period)`) restituisce l'intervallo con l'istante fissato. Per un periodo «Intervallo» restituisce i
  suoi estremi, come oggi.
- Tutte le liste e i grafici nominati sopra usano l'hook al posto di `listIntervalOf(…, new Date())` nel render. Nessun
  `new Date()` resta nel render di una funzionalità per calcolare un intervallo, e lo prova un test di architettura o una
  regola ESLint.
- Le riletture ogni 30 secondi continuano a portare i dati nuovi: l'intervallo di un periodo recente ha solo l'inizio,
  la fine è aperta.
- Prova: per ogni lista paginata, un test che sposta l'orologio di un minuto prima di «Altri» e trova la pagina
  successiva aggiunta a quelle già lette. Un test dell'hook prova che l'intervallo cambia quando cambia il periodo.

## Alternative scartate

- Inizio calcolato a ogni render ma tolto dalla chiave della query: la rilettura chiederebbe un intervallo diverso da
  quello della chiave, e la cache non sarebbe più la fotografia di una richiesta.
- Inizio arrotondato all'ora o al giorno: sposta il problema al cambio d'ora e contraddice ADR periodo-al-minuto.

## Conseguenze

- Con la pagina aperta a lungo, «ultimi 30 minuti» parte dal momento della scelta. Riscegliere il periodo o riaprire la
  pagina ricalcola l'inizio.
