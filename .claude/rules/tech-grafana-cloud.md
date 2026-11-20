---
paths:
  - "src/autotrading/adapters/outbound/grafana_cloud/**"
  - "tests/unit/adapters/grafana_cloud/**"
---

# Adapter in uscita: Grafana Cloud

- Sistema integrato: Grafana Cloud, piano gratuito (ADR telemetria-opentelemetry-verso-grafana-cloud). È l'unica
  cartella che importa `opentelemetry` (SDK, esportatore OTLP HTTP/protobuf, strumentazioni di FastAPI, httpx,
  SQLAlchemy e del `logging` standard), dichiarata in `TECHNOLOGY_LIBRARIES`. Nessun collector sulla macchina: api e
  worker esportano in OTLP diretto.
- **Nessuna porta**: domain e application non cambiano, la telemetria è solo strumentazione automatica.
  `composition.py` offre `grafana_cloud_telemetry_adapters(source, service_name)`, che `bootstrap.py` chiama per prima
  in `create_application` (`autotrading-api`) e in `create_worker_application` (`autotrading-worker`): le
  strumentazioni vedono così ogni applicazione FastAPI, client httpx ed engine SQLAlchemy creati dopo. Per questo
  `fastapi.FastAPI` e `sqlalchemy.create_engine` si chiamano attraverso il modulo, non importati per nome.
- **Configurazione**: `GRAFANA_OTLP_ENDPOINT` e `GRAFANA_INSTANCE_ID` (pubblici) e il token da
  `GRAFANA_OTLP_TOKEN_FILE`, file montato in sola lettura; autenticazione Basic con `instance_id:token` in base64,
  costruita in `telemetry.py`. Con una delle tre impostazioni vuota o assente la telemetria è spenta e il servizio parte
  come oggi. **Mai** il token in variabili d'ambiente (`OTEL_EXPORTER_OTLP_HEADERS` compreso).
- **Segnali**: tracce di FastAPI, httpx e SQLAlchemy; le metriche di quelle strumentazioni, esportate ogni 60 secondi;
  i record del `logging` standard dal livello INFO, con la traccia corrente. Risorsa: `service.name`,
  `service.version` (`APP_VERSION`), `deployment.environment` (`APP_ENVIRONMENT`). I log su stdout restano.
- **Nessun segreto esportato**: il campionatore toglie la query string da ogni URL e non crea span per
  `api.telegram.org`, che ha il token del bot nel percorso; nessuna intestazione HTTP registrata; gli span SQL portano i
  segnaposto, mai i valori. I record dei logger `httpx`, `httpcore` (URL interi) e `opentelemetry` (gli errori
  dell'esportatore stesso) non si esportano. Il token non compare in log, errori o repr.
- Il forecaster resta escluso: non ha segreti (ADR 0107).
- Test: unit test con esportatori in memoria e un ricevitore OTLP locale; il servizio intero con la telemetria accesa
  in un processo a sé, perché i provider di OpenTelemetry sono globali e si impostano una volta sola.
