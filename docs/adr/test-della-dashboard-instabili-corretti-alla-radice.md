# ADR test-della-dashboard-instabili-corretti-alla-radice — Test della dashboard instabili corretti alla radice

- Stato: proposta (22 novembre 2026)
- Requisiti: Bug 714, Task 715
- Collegate: ADR test-della-dashboard-deterministici, `.claude/rules/tech-dashboard.md` §Prove, `.claude/rules/tests.md`
- Verifica: prova

## Contesto e problema

Dopo il Bug 610 due test della dashboard tornano a fallire a caso. `source-credentials.test.tsx` («configures the
adapter with a secret field…») scade su un `waitFor` da 1 s quando la suite gira in ordine casuale, mentre da solo
passa. `cash-out-profits.test.tsx` fallisce anche da solo, in 2 esecuzioni su 4. Un rosso non riproducibile nei
controlli obbligatori blocca le PR senza indicare un difetto.

## Fattori decisionali

- ADR test-della-dashboard-deterministici: ogni causa si corregge alla radice. Nessun nuovo tentativo, nessuna prova
  disattivata. Un timeout più alto è ammesso solo per un costo fisso misurato e non riducibile, col motivo in un
  commento.
- Proprietario (21/11/2026): nessun test escluso o saltato; un test rotto è subito un Bug.

## Decisione

- Si riproduce ogni errore prima di correggerlo: l'esecuzione isolata ripetuta per `cash-out-profits.test.tsx`,
  `npm run test:stability` per `source-credentials.test.tsx`. Il resoconto nomina causa e correzione per ogni test.
- Le cause attese, da confermare riproducendo:
  - stato condiviso tra test (fake, cronologia del router, cache delle query);
  - attese su testi o ruoli che compaiono prima che i dati siano arrivati;
  - azioni dell'utente non attese prima dell'asserzione;
  - timer reali dove il test dipende dal tempo.
- Le correzioni stanno nei test o nei fake di `src/testing/`. Il codice di produzione cambia solo se la causa è un
  difetto suo (es. un aggiornamento di stato dopo lo smontaggio), e allora la correzione ha un test che lo prova.
- Ogni altro test che la prova di stabilità fa fallire durante il lavoro si corregge nello stesso modo, nella stessa PR.
- Prova: `npm run test:stability` passa 10 volte di fila, e `cash-out-profits.test.tsx` passa 20 esecuzioni isolate
  di fila.

## Alternative scartate

- Alzare `asyncUtilTimeout` o il timeout dei test: nasconde la causa (ADR test-della-dashboard-deterministici).
- Nuovi tentativi in Vitest: un test instabile resta instabile.

## Conseguenze

- Un rosso nei controlli della dashboard torna a indicare sempre un difetto vero.
