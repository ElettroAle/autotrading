# ADR 0015 — PostgreSQL nel compose, due ruoli, segreti generati sulla macchina

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.1.2, R0.1.3

## Contesto

R0.1.2 chiede che il tenant di un utente nasca al primo accesso e resti lo stesso dopo: serve uno
stato persistente. L'architettura (§4, §8.2, §12.1) ha già scelto PostgreSQL 16 in container, row
level security per tenant e segreti dei servizi come file montati, mai variabili d'ambiente. Restano
da decidere: chi applica le migrazioni, con quale ruolo, da dove arriva la password del database e
come si provano gli adapter contro un PostgreSQL vero senza Docker sulla macchina di sviluppo.

## Decisione

- **Servizio `postgres`** nel compose, immagine ufficiale `postgres:16.15-alpine` fissata per digest,
  dati in un volume, nessuna porta pubblicata: lo raggiungono solo i container della stessa rete.
- **Due ruoli.** `autotrading_owner` crea il database e possiede le tabelle; applica le migrazioni.
  `autotrading_app` è il ruolo con cui lavorano gli adapter: accede ma non possiede nulla, quindi la
  row level security con `FORCE` vale sempre per lui (rule `tech-sqlalchemy`). Lo crea lo script
  `deploy/postgres/10-application-role.sh` alla prima inizializzazione dei dati.
- **Migrazioni** con Alembic dal servizio `migrate`: stessa immagine dell'API, entra come proprietario,
  applica `upgrade head` e termina. L'API parte solo se le migrazioni sono riuscite
  (`service_completed_successfully`); se falliscono, il controllo di salute del rilascio fallisce.
- **Segreti generati sulla macchina.** `deploy/prepare-installation.sh`, lanciato dal rilascio prima di
  `docker compose up`, crea le due password se mancano, con 40 caratteri casuali, leggibili solo
  dall'utente dell'immagine dell'API (65532) e dal gruppo di postgres (70). Le password non passano da
  GitHub né da una persona, come le chiavi delle credenziali (ADR 0007). Arrivano ai container come
  secret del compose, cioè file montati in sola lettura.
- **Test di integrazione** in CI: il job `test` ha un servizio PostgreSQL e lancia anche il marker
  `integration`. Ogni modulo di test crea un database nuovo, applica le migrazioni da zero con il
  proprietario e prova l'adapter con il ruolo applicativo. In locale, senza PostgreSQL, i test di
  integrazione restano esclusi dalla suite di default.
- **Driver** `psycopg` 3 (binario), SQLAlchemy 2 sincrono.

## Alternative scartate

- **Migrazioni all'avvio dell'API**: l'API dovrebbe avere la password del proprietario, e il ruolo
  applicativo non sarebbe più l'unico con cui l'API parla al database.
- **Password nei secret degli environment GitHub**: una persona con accesso alle impostazioni del
  repository potrebbe sostituirla e la pipeline la maneggerebbe; generata sulla macchina, non esce mai.
- **Un solo ruolo proprietario anche per l'applicazione**: il proprietario delle tabelle aggira la row
  level security senza `FORCE`, e un errore di configurazione toglierebbe la seconda barriera.
- **SQLAlchemy asincrono**: l'SDK Hyperliquid è sincrono e il carico è minimo; l'asincrono aggiunge
  complessità senza un beneficio misurabile oggi.

## Conseguenze

- Il primo rilascio dopo questa decisione crea il volume dei dati e le due password sulla macchina.
- La perdita del volume perde tenant e conti; in E0 non c'è backup (architettura §12.1).
- Le migrazioni devono restare compatibili con l'API in esecuzione durante il rilascio.
- `domain` e `application` non possono importare `sqlalchemy`, `alembic` né `psycopg` (contratto di
  import-linter).
