# ADR riquadri-dei-flussi-separati — Riquadri dei flussi separati

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 572, Task 573
- Collegate: `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

`features/flows/components/flows-list.tsx:24-32` rende i flussi in un unico `<ul>` con bordo e `divide-y`: i riquadri
risultano attaccati.

## Fattori decisionali

- Bug 572; stessa forma dei riquadri delle altre pagine (Conti a riquadri, Bug 565).

## Decisione

- `<ul className="space-y-3">` e ogni `<li>` un riquadro con bordo, angoli arrotondati, sfondo e padding propri.
- Prova: ogni flusso è un riquadro distinto con lo spazio fra i riquadri.

## Alternative scartate

- Solo più padding nel `divide-y`: resta un blocco unico.

## Conseguenze

- Nessuna.
