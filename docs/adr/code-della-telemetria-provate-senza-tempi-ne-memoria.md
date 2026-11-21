# ADR code-della-telemetria-provate-senza-tempi-ne-memoria — I limiti delle code della telemetria si provano in modo deterministico

- Stato: proposta (21 novembre 2026)
- Requisiti: Bug 687 (Task 693); R6.1.x (telemetria verso Grafana Cloud)
- Collegate: ADR telemetria-opentelemetry-verso-grafana-cloud; ADR nessun-test-escluso-o-saltato
- Verifica: prova

## Contesto e problema

`tests/unit/adapters/grafana_cloud/test_unreachable_grafana_cloud.py::test_spans_and_records_beyond_the_queues_are_dropped_without_growing_the_memory`
avvia un processo, emette 30.000 span e record sotto `tracemalloc` e pretende che finisca entro 60 secondi e cresca meno di
5 MB. Sotto carico (suite completa in parallelo con Playwright) il tempo o la memoria superano la soglia: il test fallisce
a caso nella variante `[never-answers]` e passa da solo. Un test che dipende dal carico della macchina non prova nulla.

## Fattori decisionali

- `CLAUDE.md` e `.claude/rules/tests.md`: gli unit test sono deterministici; ogni test gira nella pipeline e nessuno si
  salta (ADR nessun-test-escluso-o-saltato).
- `telemetry_providers(resource, spans, metric_reader, logs)` riceve gli exporter: si può provare con exporter finti senza
  installare i provider globali.
- Ciò che va provato (ADR telemetria): con l'esportazione bloccata il servizio non attende e le code restano limitate.

## Decisione

- **Code limitate, nello stesso processo**: un unit test costruisce i provider con `telemetry_providers` ed exporter finti
  che restano bloccati su un evento finché il test non li libera. Emette span e record pari a più volte la capacità della
  coda (2048) e verifica che: l'emissione ritorni (il thread dell'emissione termina; l'unica attesa è una guardia contro il
  blocco, non una soglia di prestazione); gli elementi trattenuti dai processori non superino la capacità della coda,
  letti contando ciò che l'exporter riceve dopo lo sblocco (al più una coda più i lotti già in esportazione). Niente
  `tracemalloc`, niente soglie di tempo o di memoria.
- **Richieste che non attendono l'esportazione** (`test_a_request_answers_without_waiting_for_the_export_to_an_unreachable_grafana_cloud`):
  resta sul processo con l'endpoint irraggiungibile vero, ma il processo smette di caricare i 30.000 record sotto
  `tracemalloc`; la soglia di 3 secondi resta, molto sotto i 10 secondi di attesa di un'esportazione OTLP.
- Il test di memoria e carico nel processo separato si toglie: lo sostituisce la prova delle code.

## Alternative scartate

- Alzare le soglie di tempo e memoria: sposta il problema, il test resta dipendente dal carico.
- Eseguire il test da solo o in serie: la suite resta con un test che dipende da come gira.

## Conseguenze

- Il limite delle code è provato in modo deterministico e veloce; la suite non ha più un test instabile.

## Prove

- Il test nuovo visto rosso con una coda illimitata (capacità della coda alzata oltre il numero emesso) e con un exporter
  che blocca l'emissione; verde ripristinato. Suite completa eseguita due volte in parallelo con Playwright senza
  fallimenti.
