# ADR eccezioni-delle-vulnerabilita-npm-con-scadenza — Advisory senza correzione accettate con motivo e scadenza

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 590, Task 591; F0.5 (integrazione e rilascio)
- Collegate: `.claude/rules/ci.md`, `.github/actions/npm-audit/action.yml`
- Verifica: prova

## Contesto e problema

Il job `quality / vulnerabilità` esegue `npm audit --audit-level=low` nella dashboard: qualunque vulnerabilità blocca.
GHSA-fc5q-39xc-vjpf (ReDoS in picomatch, alta, aggiornata il 17/11/2026) vale per tutte le versioni fino alla 4.0.7,
l'ultima pubblicata: nessuna correzione esiste, e picomatch è dentro vite, vitest, eslint e Playwright, quindi non si
può sostituire. Il controllo blocca ogni PR.

## Fattori decisionali

- Decisione del proprietario (17/11/2026): una libreria esistente, `better-npm-audit`, non uno script nostro.
- Una vulnerabilità nuova resta sempre bloccante; un'eccezione dura poco e si rivede alla scadenza.
- `npm audit --omit=dev` dà 0 vulnerabilità: picomatch non finisce nell'immagine.

## Decisione

- `better-npm-audit` (MIT, 4.2.1) come dipendenza di sviluppo della dashboard; l'azione `npm-audit` esegue
  `better-npm-audit audit` con livello `low` al posto di `npm audit --audit-level=low`.
- Le eccezioni stanno in `dashboard/.nsprc`: per ogni advisory id, `active`, `notes` (motivo e dove arriva) ed
  `expiry` a 14 giorni dalla data in cui si aggiunge. Prima voce: GHSA-fc5q-39xc-vjpf, nessuna correzione, solo
  strumenti di sviluppo.
- Alla scadenza il controllo torna rosso: si verifica se la correzione esiste (si aggiorna e si toglie la voce) o si
  rinnova con una nuova scadenza in una PR.
- Prova: test in `tests/architecture` (o della pipeline in `tools/`) che verifica che ogni voce di `.nsprc` abbia
  note e una scadenza al più 14 giorni dopo la data in cui è stata aggiunta, e che l'azione usi `better-npm-audit`.

## Alternative scartate

- Script nostro con il rosso appena esce la correzione: scartato dal proprietario a favore della libreria.
- `npm audit --omit=dev`: gli strumenti di sviluppo non sarebbero più controllati.
- Attendere la correzione: nessuna PR si integrerebbe.

## Conseguenze

- Ogni 14 giorni un'eccezione aperta richiede una scelta esplicita.
