# ADR telemetria-opentelemetry-verso-grafana-cloud — Tracce, metriche e log di api e worker verso Grafana Cloud

- Stato: proposta (20 novembre 2026)
- Requisiti: Task 378 T6.1.2 (F6.1 Infrastruttura)
- Collegate: ADR 0007, ADR 0015, ADR 0071 (segreti esterni dalla pipeline), ADR 0107 (forecaster senza segreti),
  ADR 0162 e ADR 0165 (limiti di memoria misurati); `.claude/rules/layer-adapters.md`, `.claude/rules/ci.md`,
  `.claude/rules/tech-forecaster.md`
- Verifica: prova

## Contesto e problema

T6.1.2 chiede tracce, metriche e log strutturati con OpenTelemetry, esportati verso Grafana Cloud piano gratuito, con
le credenziali come file montato in sola lettura, nessun container in più e la libreria confinata nel suo adapter.
Oggi i servizi scrivono solo log testuali su stdout (`deploy/logging.json`). Il proprietario ha creato lo stack
Grafana Cloud (regione EU) e messo il token nel segreto `GRAFANA_OTLP_TOKEN` dell'environment `dev`.

## Fattori decisionali

- Decisioni del proprietario (backlog E6, 15 novembre 2026): OpenTelemetry verso Grafana Cloud gratuito, nessun
  container in più (niente collector: i servizi esportano in OTLP diretto).
- CLAUDE.md: un adapter = un sistema integrato, una libreria in una sola cartella; configurazione per adapter con
  `ConfigurationSource`; `bootstrap.py` senza decisioni; mai segreti in variabili d'ambiente.
- ADR 0071: un segreto creato fuori dalla macchina arriva dal segreto dell'environment via stdin di Tailscale SSH e
  diventa un file 0400.
- ADR 0107 e `tech-forecaster.md`: il forecaster non ha segreti. Il token OTLP è un segreto.
- Limiti del piano gratuito: 10.000 serie attive di metriche, 50 GB al mese di log e di tracce, 14 giorni.
- Nessun segreto in log, errori o repr: vale anche per ciò che si esporta.

## Decisione

- **Adapter `adapters/outbound/grafana_cloud/`**: il sistema integrato è Grafana Cloud. È l'unica cartella che
  importa `opentelemetry-*` (SDK, esportatore OTLP HTTP/protobuf, strumentazioni di FastAPI, httpx, SQLAlchemy e del
  `logging` standard), dichiarate in `TECHNOLOGY_LIBRARIES`. `composition.py` offre
  `grafana_cloud_telemetry_adapters(source, service_name)` (in `bootstrap.py` la sorgente va solo a funzioni `*_adapters`): installa provider di tracce, metriche e log e le strumentazioni automatiche; `bootstrap.py` la chiama
  per prima in `create_application` (servizio `autotrading-api`) e in `create_worker_application`
  (`autotrading-worker`). Domain e application non cambiano: nessuna porta, solo strumentazione automatica.
- **Segnali**: tracce delle richieste FastAPI, delle chiamate httpx e delle query SQLAlchemy; le metriche che quelle
  strumentazioni producono (durata delle richieste HTTP in ingresso e in uscita), esportate ogni 60 secondi; i record
  del `logging` standard dal livello INFO, con la traccia corrente, inviati come log OTLP. I log su stdout restano.
  Attributi della risorsa: `service.name`, `service.version` (`APP_VERSION`), `deployment.environment`
  (`APP_ENVIRONMENT`).
- **Nessun segreto esportato**: gli span httpx registrano l'URL senza query string; le chiamate a `api.telegram.org`,
  che hanno il token del bot nel percorso, non producono span; nessuna intestazione HTTP registrata; gli span SQL
  portano il testo con i segnaposto, mai i valori.
- **Configurazione** (`configuration.py`): `GRAFANA_OTLP_ENDPOINT` e `GRAFANA_INSTANCE_ID` (pubblici) e il token da
  `GRAFANA_OTLP_TOKEN_FILE`; autenticazione Basic con `instance_id:token` in base64, costruita nell'adapter. Endpoint,
  istanza o token vuoti o assenti: telemetria spenta, il servizio parte come oggi (come il bot Telegram senza token).
- **Pipeline**: endpoint e istanza sono variabili dell'environment GitHub (`vars.GRAFANA_OTLP_ENDPOINT`,
  `vars.GRAFANA_INSTANCE_ID`), scritte nel `.env` come le altre; il compose le passa ad api e worker con
  `GRAFANA_OTLP_TOKEN_FILE: /run/secrets/grafana_otlp_token`. Il token segue l'ADR 0071: `prepare-installation.sh`
  crea il file vuoto, uno script come `install-telegram-token.sh` lo scrive da stdin in modo atomico (0400, utente
  65532), e un token cambiato ricrea api e worker.
- **Forecaster escluso**: dargli il token violerebbe l'ADR 0107 («nessun segreto»). Le sue chiamate risultano dagli
  span httpx del worker (durata, esito); i suoi log restano su stdout.
- `.claude/rules/tech-grafana-cloud.md`, la cartella `grafana_cloud/` nell'elenco degli adapter in uscita e la riga
  nell'indice delle rule di `CLAUDE.md`.

## Alternative scartate

- Collector o Grafana Alloy sulla macchina: un container in più, escluso dal proprietario.
- Cartella `opentelemetry/`: nomina la libreria, non il sistema integrato (CLAUDE.md).
- Variabili `OTEL_EXPORTER_OTLP_HEADERS` con il token: segreto in variabile d'ambiente, vietato.
- Token anche al forecaster: contraddice l'ADR 0107; resta una scelta del proprietario.

## Conseguenze

- Ogni servizio con telemetria accesa usa un po' più di memoria e di rete: i limiti del compose si rivedono con la
  misura di ogni rilascio (ADR 0162).
- Senza token, in locale e nei test, nulla viene esportato.
- Volumi attesi ben sotto il piano gratuito; nessun campionamento delle tracce finché non serve.
