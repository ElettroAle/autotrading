# ADR 0165 — Limiti di memoria di ogni servizio dal consumo misurato

- Stato: proposta (15 novembre 2026)
- Requisiti: Bug 252 (Task 254)
- Collegate: ADR 0162 (misura a ogni rilascio), ADR 0107 (`mem_limit: 768m` del forecaster), ADR 0144 (tipo
  d'istanza `d2-4`), ADR 0148 (LiteLLM come libreria nel worker), Bug 250 (macchina bloccata al rilascio)

## Contesto e problema

In `deploy/compose.yaml` solo il forecaster ha un limite di memoria. Un servizio che sfora consuma la memoria della
macchina (4 GiB, `d2-4`) fino a bloccarla, compresi Docker e Tailscale: la macchina non si raggiunge più e il rilascio
resta appeso. La misura dell'ADR 0162 sul rilascio di dev del 14 novembre 2026 (run 43655021533) dà, in MiB:

| Servizio | Picco | Riposo |
|---|---:|---:|
| worker | 302 | 303 |
| api | 138 | 138 |
| forecaster | 110 | 108 |
| postgres | 52 | 51 |
| dashboard | 30 | 29 |

Memoria disponibile minima durante il rilascio: 2515 MiB. La misura non vede i picchi dei cicli dei flussi (chiamate
ai modelli, grafo del ciclo, addestramenti del forecaster) né le query pesanti di PostgreSQL.

## Fattori decisionali

- ADR 0107: il limite del forecaster esiste perché un addestramento non tolga memoria agli altri servizi; resta
  `768m`.
- ADR 0162, Conseguenze: i picchi dei cicli restano fuori dalla misura, il limite tiene un margine sopra il riposo.
- Somma dei limiti entro la RAM della macchina, lasciando spazio a sistema, Docker, Tailscale e al pull delle immagini.
- Tutti i servizi a lunga vita hanno `restart: unless-stopped`: un servizio fermato dal limite riparte da solo, la
  macchina resta raggiungibile.
- Nessun costo nuovo (nessun cambio di tipo d'istanza).

## Opzioni considerate

### 1. `mem_limit` per servizio, circa due volte e mezzo il riposo misurato, arrotondato

- Pro: un servizio che sfora viene fermato e riavviato da Docker senza toccare gli altri né la macchina; somma
  2432 MiB, sotto i 4 GiB con circa 1,5 GiB per sistema e pull.
- Contro: un picco reale dei cicli oltre il limite riavvia il servizio; il limite va rivisto col dato dei rilasci.

### 2. Limiti stretti sul riposo misurato più un margine fisso piccolo

- Pro: più memoria libera per il pull.
- Contro: la misura non contiene i picchi dei cicli; il worker e PostgreSQL verrebbero riavviati nel lavoro normale.

### 3. Nessun limite, solo `oom_score_adj` per far scegliere al kernel chi fermare

- Pro: nessun numero da tarare.
- Contro: il kernel interviene solo a memoria esaurita, quando la macchina è già degradata (Bug 250).

## Esito della decisione

Opzione 1. In `deploy/compose.yaml`:

| Servizio | `mem_limit` | Motivo |
|---|---:|---|
| worker | `768m` | riposo 303 MiB; LiteLLM e grafo del ciclo crescono durante un ciclo |
| forecaster | `768m` | invariato (ADR 0107) |
| api | `384m` | riposo 138 MiB |
| postgres | `384m` | riposo 51 MiB; `shared_buffers` di default (128 MB) più le query dello storico |
| dashboard | `128m` | riposo 29 MiB, server di file statici |

Il `migrate` gira una volta a ogni rilascio e finisce prima dell'avvio degli altri: `256m`. Somma dei servizi a lunga
vita 2432 MiB. Una prova legge `deploy/compose.yaml` e verifica che ogni servizio abbia `mem_limit` e che la somma dei
servizi a lunga vita resti entro 2560 MiB.

Nel rapporto dell'ADR 0162 la riga di un container in riavvio, che `docker stats` mostra come `--`, non è un servizio:
si esclude dal rapporto.

Verifica: prova (ogni servizio del compose ha `mem_limit`; somma entro 2560 MiB; nessuna riga `--` nel rapporto).

### Conseguenze

- Un servizio che sfora si riavvia da solo e la macchina resta raggiungibile; il riavvio si vede nei log del servizio.
- Ogni rilascio porta nel riepilogo e nel log il consumo dei servizi: i limiti si rivedono con lo stesso dato.
- Un servizio nuovo nasce con il suo `mem_limit`, o la prova lo segnala.
