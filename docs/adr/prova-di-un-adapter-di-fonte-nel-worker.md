# ADR prova-di-un-adapter-di-fonte-nel-worker — Prova di un adapter di fonte eseguita dal worker senza registrare

- Stato: proposta (19 novembre 2026)
- Requisiti: US 404 R6.3.1, Task 405
- Collegate: ADR fonti-con-adapter-dichiarati, ADR credenziali-degli-adapter-delle-fonti, ADR 0021 (worker via HTTP
  interno), ADR 0105 (fonti del ciclo e attesa), ADR permanenza-decisa-dall-errore-base, ADR 0048, ADR 0049;
  `.claude/rules/context-sources.md`, `.claude/rules/tech-worker.md`, `.claude/rules/tech-fastapi.md`
- Verifica: prova

## Contesto e problema

R6.3.1 vuole provare una fonte dalla dashboard con la stessa lettura del ciclo e vederne esito, valori, istante dei
dati, tempo di risposta e, in caso di errore, il motivo con l'indicazione transitorio o permanente; la prova non
registra valori nei cicli e non tocca i flussi. Con R4.1.1 e R4.1.2 la prova è per adapter e usa le credenziali del
tenant, che solo il worker apre. Oggi la lettura passa da `CollectSourceUseCase`, che registra i campioni, e il lettore
del forecast registra la previsione.

## Fattori decisionali

- R6.3.1: «la stessa lettura del ciclo»; nessuna registrazione; errore come nel ciclo (R1.2.5).
- Credenziali leggibili solo dal worker (ADR 0007, ADR credenziali-degli-adapter-delle-fonti).
- La permanenza la decide l'errore base (`AutotradingError.permanent`).
- Il caso d'uso orchestra; un caso d'uso per modulo.

## Decisione

- **Domain `sources`**: `SourceTrial` (esito `riuscita` o `errore`, valori letti `tuple[SourceValue, ...]`, istante
  dei dati = il più recente `reference_at` dei valori, tempo di risposta in millisecondi, motivo e `permanent` per
  l'errore).
- **Application `sources`**: `TrySourceAdapterUseCase` con `TrySourceAdapterCommand(source, adapter, asset | None,
  parameters)`. Passi: definizione e adapter dal catalogo (404 se assenti); parametri validati dal catalogo (valore
  fuori dai limiti = 422 con parametro e limiti, la lettura non parte); asset richiesto solo per una fonte per asset;
  credenziali dell'adapter aperte come nel ciclo (assenti = esito errore col motivo «configura l'adapter …»); lettura
  con lo stesso lettore del ciclo, sotto `ConcurrentCallsPort` con la stessa attesa predefinita delle fonti del ciclo;
  tempo misurato con la porta dell'orologio. Un errore tipizzato diventa esito `errore` con `str(error)` e
  `error.permanent`; un'attesa scaduta è `errore` transitorio «nessuna risposta entro N secondi», come nel ciclo.
- **Stessi lettori, nessuna registrazione**: la costruzione dei lettori per (fonte, adapter) oggi in
  `CollectCycleSourceUseCase` si estrae in un'unica funzione dell'application usata da ciclo e prova; la prova chiama
  il lettore direttamente, senza `CollectSourceUseCase` né `SampleRepositoryPort`. `SourceRequest.flow_id` diventa
  facoltativo: senza flusso il lettore del forecast non registra la previsione. Gli indicatori usano l'intervallo di
  ciclo predefinito del flusso.
- **Worker e API**: rotta del worker `POST /tenants/{tenant_id}/sources/{source}/adapters/{adapter}/trials`
  (in `WorkerUseCases`), client in `adapters/outbound/worker/` che realizza la porta della prova nell'API; rotta
  dell'API `POST /sources/{source}/adapters/{adapter}/trials` con `{asset, parameters}`. La risposta è 200 con
  l'esito anche quando la lettura fallisce (l'errore della fonte è il risultato della prova); 404 e 422 solo per
  fonte o adapter sconosciuti e parametri non validi; worker irraggiungibile = 503 come le altre chiamate al worker.

## Alternative scartate

- Usare `CollectSourceUseCase` con un repository dei campioni che scarta: il forecast registrerebbe comunque e la
  prova dipenderebbe da un finto in produzione.
- Eseguire la prova nell'API: non può aprire le credenziali degli adapter.

## Conseguenze

- Ciclo e prova condividono i lettori: un adapter nuovo è provabile senza codice in più.
