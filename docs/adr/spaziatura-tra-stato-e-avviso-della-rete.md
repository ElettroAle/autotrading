# ADR spaziatura-tra-stato-e-avviso-della-rete — Badge di stato e avviso della rete separati

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 581, Task 582
- Collegate: `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

In `features/flows/components/flow-view.tsx` il badge di stato («Bozza») e `TestNetworkNotice` sono attaccati.

## Fattori decisionali

- Spaziatura standard di Tailwind già usata negli altri contenitori della dashboard.

## Decisione

- Il badge e l'avviso stanno in un contenitore `flex flex-wrap items-center gap-2` (o con `gap` del layout della
  pagina), senza margini ad hoc sui componenti condivisi. Una prova verifica che i due elementi stanno nel contenitore
  con lo spazio.

## Alternative scartate

- Margine dentro `TestNetworkNotice`: cambierebbe il componente condiviso in tutte le pagine.

## Conseguenze

- Nessuna.
