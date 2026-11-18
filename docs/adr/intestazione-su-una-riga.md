# ADR intestazione-su-una-riga — La barra in alto sta su una riga a ogni larghezza

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 592, Task 594
- Collegate: ADR area-utente-in-alto-a-destra, ADR 0145 (comando Indietro nell'intestazione), ADR 0119,
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

`components/layouts/app-header.tsx` usa `flex-wrap`: su un telefono Menu, Indietro, «AutoTrading», il distintivo
dell'installazione e il nome dell'utente non stanno su una riga, l'area utente va a capo e la barra raddoppia
coprendo il contenuto (segnalazione del proprietario, 17/11/2026).

## Fattori decisionali

- Segnalazione del proprietario: la barra non deve sovrapporsi né andare a capo.
- Bersagli di tocco di almeno 44 px (`min-h-11 min-w-11`) e nome accessibile per ogni comando (tech-dashboard.md).
- Componenti condivisi: la barra è una sola, in `components/layouts`.

## Decisione

- La barra non va mai a capo (`flex-nowrap`); la parte sinistra può restringersi (`min-w-0`), la destra no.
- Sotto i 768 px: Menu diventa un pulsante con l'icona del menu e `aria-label="Menu"`; Indietro mostra solo la freccia
  con il testo «Indietro» riservato ai lettori di schermo (`sr-only`), visibile dai 768 px; «AutoTrading» si accorcia
  con i puntini (`truncate`); l'area utente mostra solo l'icona, il nome dell'utente resta come nome accessibile del
  pulsante e come intestazione del menu, visibile dai 768 px. Il distintivo dell'installazione resta sempre.
- Dai 768 px in su la barra resta com'è.
- Prove: unit test di barra, Indietro e area utente (nomi accessibili invariati); prova di layout a 320 e 360 px:
  la barra ha l'altezza di una riga e nessun elemento esce dallo schermo.

## Alternative scartate

- Nascondere il distintivo dell'installazione su telefono: dice su quale installazione si sta operando.
- Spostare Indietro nel corpo della pagina: contraddice l'ADR 0145.

## Conseguenze

- La barra ha la stessa altezza su ogni schermo.
