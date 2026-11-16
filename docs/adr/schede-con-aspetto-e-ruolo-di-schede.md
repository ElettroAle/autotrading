# ADR schede-con-aspetto-e-ruolo-di-schede — Schede con aspetto e ruolo di schede

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.5 (429), Task T6.4.5.1 (430)
- Collegate: ADR 0116 (struttura della dashboard), ADR viste-e-comandi-della-pagina-del-flusso

## Contesto e problema

`src/components/ui/view-tabs.tsx` disegna le schede (elenco e classifica dei flussi, storico, viste del flusso) come
testo con una sottolineatura: il proprietario le vede come semplici collegamenti (feedback del 16/11/2026).

## Fattori decisionali

- R6.4.5: aspetto da schede sobrio e coerente, scelta evidente, ruolo accessibile e tastiera.
- Decisione del proprietario (16/11/2026): priorità all'usabilità, grafica come quella attuale.
- `.claude/rules/tech-dashboard.md`: Tailwind, componenti condivisi in `src/components`.

## Opzioni considerate

1. Evolvere `ViewTabs`: barra con sfondo leggero, scheda scelta con sfondo bianco, testo scuro e indicatore blu,
   schede non scelte come comandi tenui; ruoli `tablist`/`tab` con `aria-selected` quando le schede cambiano vista
   nella stessa rotta, collegamenti con `aria-current="page"` quando le schede sono rotte; frecce da tastiera;
   una riga con scorrimento interno su schermi stretti.
2. Una libreria di componenti: scartata, nessuna libreria UI nello stack della dashboard.

## Esito della decisione

Opzione 1, in un solo componente usato da tutte le schede della dashboard; nessun nome accessibile cambia.

Verifica: prova (scenari di R6.4.5, unit test del componente, prova di layout a 360 pixel).

### Conseguenze

- Le schede si riconoscono in tutta la dashboard; la pagina del flusso a schede (R6.4.3) le riusa.
