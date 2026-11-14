# ADR 0117 — La dashboard è un container statico servito sul percorso `/dashboard` dello stesso nome Tailscale

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.1.1 (Task T2.1.1.2)
- Collegate: docs/architecture.md §2 (container `dashboard`, build statica), ADR 0013 (accesso solo dalla tailnet
  con Tailscale Serve), ADR 0111 (rilascio riuscito solo con tutti i servizi sani), ADR 0116 (regole della dashboard)

## Contesto e problema

Il proprietario ha scelto un container `dashboard` separato da `api` (avvio di E2, 14 novembre 2026). Va deciso come
la dashboard si raggiunge dalla tailnet, come chiama l'API e come entra nel rilascio, senza nuove risorse cloud,
senza toccare i security group e senza riprovisionare dev (si perderebbe il database).

## Decisione

- Immagine `dashboard` costruita dalla pipeline insieme a quella dell'applicazione, con lo stesso digest promosso da
  dev a prod (ADR 0001-0013): build Vite in uno stadio Node, servita da un server statico non privilegiato in sola
  lettura, con fallback a `index.html` per le rotte della SPA e un `/dashboard/health` per l'healthcheck di compose.
- Tailscale Serve espone la dashboard sul percorso `/dashboard` dello stesso nome HTTPS di `api`
  (`autotrading-<ambiente>.<tailnet>.ts.net`). Stessa origine dell'API: nessun CORS da aprire in `api`.
- La configurazione di Serve si applica in modo idempotente a ogni rilascio, oltre che in `cloud-init.yaml` per le
  installazioni nuove: dev si aggiorna senza riprovisioning.
- La configurazione della dashboard (issuer, client id, scope, ambiente) è servita come file `config.json` generato
  all'avvio del container dalle variabili non segrete dell'installazione: la stessa immagine vale per dev e prod.
  Nessun segreto nella dashboard (PKCE senza client secret, ADR 0118).
- Il rilascio attende anche la salute del container `dashboard` (ADR 0111).

## Alternative scartate

- **Build servita da `api`**: un container in meno, ma `api` serve anche file; il proprietario ha scelto il
  container separato.
- **Porta HTTPS dedicata (per esempio 8443)**: separa le origini, ma richiede CORS in `api` e un secondo URL da
  ricordare.
- **Configurazione cotta nella build**: un'immagine per installazione, contro la promozione dello stesso digest.

## Conseguenze

- Le rotte della dashboard vivono sotto `/dashboard/`, e la build usa quel percorso base.
- Il redirect URI di Entra è `https://autotrading-<ambiente>.<tailnet>.ts.net/dashboard/` (ADR 0118).
