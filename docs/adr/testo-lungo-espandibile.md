# ADR testo-lungo-espandibile — Componente condiviso «Leggi tutto / Riduci»

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 576, Task 577; R6.5.4 (ultima decisione), R6.5.5 (storico delle decisioni)
- Collegate: ADR 0119, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

«Ultima decisione» (`features/last-decision/components/last-decision.tsx:46`) e la scheda Decisioni
(`features/decisions/components/decisions-table.tsx:67`) accorciano il ragionamento a 160 caratteri con `shortenText`;
il testo intero non si legge lì.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): «Leggi tutto» in linea.
- Accessibilità: pulsante con `aria-expanded`, testo intero leggibile dai lettori di schermo.

## Decisione

- Nuovo componente condiviso `components/ui/expandable-text.tsx`: mostra il testo accorciato con `shortenText` e un
  pulsante «Leggi tutto» che lo espande sul posto; «Riduci» lo richiude; senza pulsante se il testo è già corto. Lo
  usano entrambi i punti.
- Prove: unit test del componente (corto, lungo, espandi, riduci) e dei due punti d'uso.

## Alternative scartate

- Tooltip al passaggio del mouse: non funziona su telefono.

## Conseguenze

- Ogni testo lungo futuro usa lo stesso componente.
