# ADR 0111 — Rilascio riuscito solo con tutti i servizi sani

- Stato: accettata (13 novembre 2026)
- Requisiti: R0.5 (rilascio in dev); Bug B1.0.5 (189)
- Collegate: ADR 0013 (installazione via Tailscale), ADR 0101 (proxy LiteLLM), ADR 0107 (forecaster)

## Contesto e problema

Il rilascio considera riuscita l'installazione quando l'api dichiara versione e ambiente attesi
(`.github/actions/health-check/action.yml`). `docker compose up -d` non attende gli healthcheck: `litellm` e
`forecaster` ne dichiarano uno ma nessuno lo aspetta, `worker` e `api` non ne hanno. Un proxy o un forecaster che non
partono lasciano il rilascio verde e i cicli senza modello o senza previsione.

## Decisione

- Ogni servizio che resta in esecuzione dichiara un healthcheck nel compose; `worker` e `api` interrogano il proprio
  `GET /health` sull'interfaccia locale del container, senza porte nuove né segreti. `migrate` è un servizio che
  termina: è pronto quando esce con successo, come già richiedono i servizi che dipendono da lui.
- Ogni avvio dell'installazione nell'action `ssh-deploy` usa `docker compose up -d --wait --wait-timeout 300`:
  Docker Compose attende che ogni servizio sia sano (o completato con successo, per i servizi da cui altri dipendono
  con `service_completed_successfully`) e fallisce altrimenti. Vale anche per la ricreazione del solo worker o del
  solo proxy dopo un token o una configurazione cambiati.
- In caso di fallimento il passo mostra stato e ultime righe di log di tutti i servizi, togliendo le righe che
  nominano una password come già prima.
- `tests/unit/deploy/test_installation.py` verifica che ogni servizio in esecuzione abbia un healthcheck e che ogni
  avvio nell'action attenda.

## Alternative scartate

- **Controllo di salute di ogni servizio dalla pipeline**: i servizi non hanno porte pubblicate e non devono averne;
  servirebbero comandi `docker inspect` scritti a mano per servizio, che Compose già offre con `--wait`.
- **`depends_on: service_healthy` tra worker, proxy e forecaster**: legherebbe l'avvio del worker a servizi senza i
  quali fallisce solo un passo del ciclo (scelta del compose attuale), senza far fallire il rilascio.

## Conseguenze

- Un rilascio che lascia un servizio non sano fallisce entro 5 minuti per ogni attesa, con lo stato dei container
  nel log del job; dev resta sui container avviati, come prima di questa decisione per l'api.
- Un servizio nuovo nel compose deve dichiarare un healthcheck, o il test diventa rosso.

## Confronto con le decisioni scritte

| Fonte | Esito |
|---|---|
| `CLAUDE.md` (Sicurezza: segreti solo come file, deploy dalla pipeline) | conforme: nessun segreto, nessuna porta, solo l'action |
| `.claude/rules/ci.md` (comandi solo nelle action, valori via `env:`) | conforme: modifica nella sola `ssh-deploy`, nessun valore interpolato |
| `docs/architecture.md` (container interni senza porte pubblicate) | conforme |

## Scostamenti

Nessuno.
