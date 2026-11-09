# ADR 0005 — Installazioni Hetzner create dalla pipeline

- Stato: superata da ADR 0008 (9 novembre 2026)
- Requisiti: R0.5.4

## Decisione

- `provision.yml`, avvio manuale per ambiente: CLI `hcloud` (verificata con checksum), server
  `autotrading-<ambiente>` Ubuntu 24.04, tipo e posizione da variabili dell'environment
  (`HCLOUD_SERVER_TYPE`, predefinito `cx23`; `HCLOUD_LOCATION`, predefinito `fsn1`).
- Configurazione versionata in `deploy/cloud-init.yaml`: utente `deploy` con sola chiave, root e
  password disabilitati, `ufw` con 22 e 443, aggiornamenti automatici, Docker.
- Firewall Hetzner con le sole porte 22 e 443, oltre a `ufw`.
- **Chiave host nota in anticipo**: la coppia di chiavi host è un segreto dell'environment e arriva
  alla macchina con cloud-init; la pipeline si collega con `StrictHostKeyChecking=yes` contro la
  chiave pubblica attesa, invece di fidarsi della prima chiave ricevuta.
- Nome pubblico `<ip-con-trattini>.sslip.io`, certificato Let's Encrypt via Caddy (TLS-ALPN su 443).
- Idempotenza per nome: se il server esiste l'esecuzione termina con "installazione <ambiente> già
  esistente" senza toccare nulla.
- Segreti negli environment GitHub `dev` e `prod`: `HCLOUD_TOKEN`, `DEPLOY_SSH_PRIVATE_KEY`,
  `HOST_SSH_PRIVATE_KEY`; variabili pubbliche `DEPLOY_SSH_PUBLIC_KEY`, `HOST_SSH_PUBLIC_KEY`.

## Alternative scartate

- **Terraform**: serve un backend per lo stato; eccessivo per due server.
- **Script locale**: fuori dalla pipeline.
- **`ssh-keyscan` al primo collegamento**: i runner sono effimeri, ogni collegamento sarebbe il
  primo e un attaccante in mezzo non verrebbe rilevato.

## Conseguenze e rischi noti

- I dati utente di cloud-init (con la chiave privata host) restano leggibili dal servizio metadati
  Hetzner dall'interno della macchina. Rischio accettato in E0: serve già un accesso alla macchina,
  e la chiave host serve solo a impersonarla verso la pipeline. Da rivedere con OpenBao.
- Le porte pubblicate da Docker non passano da `ufw`: la protezione effettiva è il firewall Hetzner.
