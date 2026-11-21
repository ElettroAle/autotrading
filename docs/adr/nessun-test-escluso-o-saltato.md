# ADR nessun-test-escluso-o-saltato — Ogni test scritto gira nella pipeline, nessuno si salta

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 642 (Task 644); Bug 643
- Collegate: ADR 0001-0013 (integrazione e rilascio); `.claude/rules/tests.md`, `.claude/rules/ci.md`, `CLAUDE.md`
  (Test, Test di architettura)
- Verifica: prova

## Contesto e problema

La suite della pipeline (`.github/actions/pytest-run/action.yml`) e quella locale (`addopts` in `pyproject.toml`)
escludono i marker `testnet`, `providers` e `sources`: 11 file di test contro sistemi veri non girano mai, e uno
(`tests/integration/hyperliquid/test_executions_testnet.py`) è rotto senza che nessun controllo lo veda. Due file
(`test_exchange_testnet.py`, `test_protections_testnet.py`) chiamano `pytest.skip` senza il file delle credenziali.
Il tag `@wip` esclude lo scenario «Al primo accesso nasce un tenant vuoto» di R0.1.2, User Story consegnata, e la
feature intera di R0.2.6, requisito non pianificato.

## Fattori decisionali

- Decisione del proprietario (21 novembre 2026, in chat): non devono esistere test saltati né esclusi; regola nel
  contratto con un test di architettura.
- Decisione del proprietario: i test contro sistemi veri (testnet, fornitori IA, fonti) girano solo nella pipeline, a
  ogni PR, mai saltati; in locale gli sviluppatori eseguono solo i test mirati. Le fonti girano contro i servizi veri,
  anche se un servizio giù blocca la PR.
- Decisione del proprietario: testnet in pipeline subito per i test di sola lettura; i test con ordini quando il
  proprietario crea il segreto con le credenziali testnet (Bug 643); lo `skip` si toglie comunque.
- Decisione del proprietario: gli scenari `@pipeline` restano provati dalla run reale della pipeline.
- Decisione del proprietario: un requisito non pianificato non ha il `.feature` in `specs/`; `@wip` sparisce.
- `CLAUDE.md`: le violazioni note di una regola di architettura stanno in `tests/architecture/known_violations.py`,
  ciascuna col Bug che la elimina, e l'elenco può solo diminuire.

## Decisione

- I marker `testnet`, `providers`, `sources` e `wip` spariscono da `pyproject.toml`: i test contro sistemi veri hanno
  il marker `integration`. `addopts` esclude in locale solo `pipeline` e `integration`; la pipeline esclude solo
  `pipeline` (più il marker del Bug 643, sotto).
- Nessun `pytest.skip`, `skipif`, `xfail`, `importorskip` né `mark.skip` nei test Python, e nessun `.skip`, `.todo`,
  `.fixme` né `.only` nei test della dashboard. Un test che vuole un file di credenziali lo legge e fallisce se manca.
- I soli test che mandano ordini sulla testnet (quelli che usano le credenziali in `test_exchange_testnet.py` e
  `test_protections_testnet.py`) hanno il marker `testnet_credentials`, che la pipeline esclude finché il Bug 643 non
  porta il segreto; ogni loro identificativo è una voce dell'elenco delle violazioni note col Bug 643.
- Regola nuova di architettura `Rule.NO_EXCLUDED_TESTS`: rossa se un test usa una delle forme di salto sopra, se la
  pipeline esclude un marker diverso da `pipeline` o se un test con un marker escluso dalla pipeline non è una voce
  nota; rossa anche se un `.feature` ha il tag `@wip`.
- `tests/scenarios/conftest.py` non tratta più `wip` come tag di selezione. Lo scenario di R0.1.2 si lega e gira;
  `specs/.../R0.2.6-rotazione-della-chiave-di-cifratura.feature` si toglie (i criteri restano sulla board).
- `tests/integration/hyperliquid/test_executions_testnet.py` passa un `AccountReference` e verifica anche i movimenti.
- `tests.md`, `ci.md` e `CLAUDE.md` dichiarano la regola.

## Alternative scartate

- Lasciare i test contro sistemi veri in un job pianificato: un test rotto si vedrebbe solo dopo l'integrazione.
- Risposte HTTP registrate per le fonti nella PR: il proprietario vuole la verifica contro i servizi veri.
- Tenere `@wip` per le User Story non consegnate: uno scenario escluso resta escluso anche dopo la consegna, come è
  successo a R0.1.2.

## Conseguenze

- La pipeline chiama testnet Hyperliquid, i fornitori IA (con una chiave inventata) e le fonti pubbliche a ogni PR: un
  servizio esterno giù o cambiato rende rossa la PR.
- I due test con ordini girano solo dopo il Bug 643; fino ad allora sono le sole voci note della regola.
