# ADR 0162 — Misura di memoria e disco dei servizi a ogni rilascio

- Stato: proposta (14 novembre 2026)
- Requisiti: Bug 252 (Task 253)
- Collegate: ADR 0144 (allineamento della macchina a ogni rilascio), ADR 0013 (accesso solo Tailscale), Bug 186 (disco
  pieno al pull), Bug 250 (macchina bloccata al rilascio)

## Contesto e problema

I limiti di memoria del Bug 252 vanno tarati sul consumo dei servizi, a riposo e nel picco del rilascio (pull e avvio),
che è il momento in cui la macchina dev si è bloccata. Una misura a mano dal PC del proprietario richiede Tailscale SSH
con verifica nel browser, e non resta: al prossimo cambio di servizi va rifatta.

## Fattori decisionali

- `CLAUDE.md`: il deploy passa sempre dalla pipeline; ADR 0013: accesso alla macchina solo da Tailscale SSH, la pipeline
  come utente `deploy`.
- Script eseguiti sulla macchina a ogni rilascio come utente `deploy`, copiati dall'action (`prepare-installation.sh`,
  `configure-serve.sh`): forma già scelta.
- Nessuno strumento di monitoraggio nell'architettura; nessun costo nuovo.

## Opzioni considerate

### 1. Campionamento durante il rilascio, rapporto nel riepilogo del job

- Pro: misura il picco proprio nel momento critico, a ogni rilascio, senza accessi a mano; il dato resta nel log del run.
- Contro: non vede i picchi dei cicli fra un rilascio e l'altro.

### 2. Servizio di monitoraggio sempre attivo sulla macchina

- Pro: vede anche i picchi dei cicli.
- Contro: un servizio in più sulla macchina che si vuole alleggerire; tecnologia non prevista dall'architettura.

## Esito della decisione

Opzione 1. `deploy/measure-resources.sh`, copiato dall'action `ssh-deploy` come gli altri script: con `start`, prima del
pull, avvia in background un campionamento ogni 2 secondi di `docker stats --no-stream` e della memoria disponibile
(`/proc/meminfo`) in un file sotto `/opt/autotrading`; con `report`, dopo `docker compose up --wait`, ferma il
campionamento e stampa per ogni container il picco e il valore a riposo in MiB, la memoria disponibile minima della
macchina durante il rilascio, `df` della radice e `docker system df`. L'action scrive il rapporto nel riepilogo del job
(`GITHUB_STEP_SUMMARY`). Il rapporto non fa mai fallire il rilascio; un rilascio fallito ferma comunque il
campionamento. Nessun segreto nel rapporto.

Verifica: prova (test sull'action e sullo script: `start` prima del pull, `report` dopo l'avvio, chiusura anche in caso
di errore).

### Conseguenze

- Ogni rilascio porta nel suo riepilogo picco e riposo dei servizi: i limiti del Task 254 si tarano su questi numeri e si
  rivedono con lo stesso dato.
- I picchi durante i cicli dei flussi restano fuori: il limite tiene un margine sopra il riposo.
