# ADR 0008 — Installazioni OVH Public Cloud create dalla pipeline

- Stato: accettata (9 novembre 2026); accesso, firewall e nome dell'installazione sostituiti dall'ADR 0013
- Requisiti: R0.5.2, R0.5.3, R0.5.4
- Sostituisce: ADR 0005

## Contesto

I piani condivisi di Hetzner non sono più disponibili, quindi l'ADR 0005 non è applicabile. Il
proprietario ha scelto OVH Public Cloud, per ora solo per l'installazione `dev`: istanze OpenStack con
cloud-init, prezzo orario o mensile, data center europei. Il resto dell'ADR 0005 resta valido:
macchina da cloud-init versionato, chiave host nota in anticipo, nome pubblico sslip.io,
idempotenza per nome.

## Decisione

- **Autenticazione**: un service account IAM OVH (OAuth2 client credentials) con una policy limitata
  al solo progetto Public Cloud; nessun utente con password, nessun token personale. La CLI OpenStack
  lo usa con `OS_AUTH_TYPE=v3oidcclientcredentials` e l'identity provider `ovhcloud-emea`.
- **Segreti e variabili negli environment GitHub**: segreti `OVH_CLIENT_ID`, `OVH_CLIENT_SECRET`,
  `DEPLOY_SSH_PRIVATE_KEY`, `HOST_SSH_PRIVATE_KEY`; variabili `OVH_PROJECT_ID`, `OVH_REGION`
  (predefinita `GRA11`), `OVH_FLAVOR` (predefinito `d2-2`), `DEPLOY_SSH_PUBLIC_KEY`,
  `HOST_SSH_PUBLIC_KEY`. Le impostazioni non segrete vanno nell'ambiente del job; id e segreto del
  service account solo nei passi che li usano.
- **CLI OpenStack in un ambiente separato su Python 3.14**: PyYAML, dipendenza della CLI, non
  pubblica ancora pacchetti per Python 3.15. `python-openstackclient` e le sue dipendenze sono fissate
  con versione e hash in `deploy/provision/requirements.txt` (generato da `requirements.in` con
  `uv pip compile --generate-hashes`), installate con `--require-hashes` in un ambiente temporaneo
  del runner. Il servizio resta su Python 3.15. Dependabot e pip-audit coprono anche questo file.
  Quando PyYAML pubblicherà i pacchetti per 3.15, la CLI torna nel lockfile del progetto.
- **Macchina** `autotrading-<ambiente>`: immagine "Ubuntu 24.04", rete pubblica `Ext-Net`,
  `deploy/cloud-init.yaml` invariato, keypair `autotrading-<ambiente>-deploy` con la chiave
  pubblica dell'utente `deploy`.
- **Firewall**: security group `autotrading-<ambiente>` con ingresso solo TCP 22 e 443 (IPv4 e
  IPv6), assegnato alla creazione al posto del gruppo predefinito, che accetta tutto; `ufw` sulla
  macchina resta.
- **Idempotenza**: se la lista dei server trova il nome, l'esecuzione termina con "installazione
  <ambiente> già esistente". Si usa la lista e non la ricerca per nome perché un errore di
  autenticazione deve far fallire l'esecuzione, non sembrare un server assente.
- **Indirizzo**: l'IPv4 della macchina su `Ext-Net`, da cui deriva il nome `<ip-con-trattini>.sslip.io`.

## Alternative scartate

- **CLI OpenStack su Python 3.15 nel lockfile del progetto**: PyYAML non si installa su 3.15.
- **CLI `ovhcloud`**: non verificato che crei istanze con cloud-init e security group.
- **Chiamate dirette alle API OpenStack da `tools/`**: molto codice in più, compresa l'autenticazione
  federata OVH.
- **API OVH con application key e consumer key**: credenziale meno standard e con privilegi più
  ampi del solo progetto.
- **Terraform**: un backend per lo stato; eccessivo per una o due macchine.

## Conseguenze e rischi noti

- D2-2 ha 1 vCPU e 2 GB: basta per E0 (api, PostgreSQL, Caddy). Con worker e forecaster si passa
  a `d2-4` cambiando la variabile `OVH_FLAVOR`.
- La documentazione OVH non dice in modo esplicito che il security group filtra la porta pubblica.
  Le porte pubblicate da Docker non passano da `ufw`, quindi il primo provisioning verifica dall'esterno
  che rispondano solo 22 e 443 (scenario di R0.5.4).
- I dati utente di cloud-init (con la chiave privata host) restano leggibili dal servizio metadati
  dall'interno della macchina, come nell'ADR 0005: rischio accettato in E0.
- Due versioni di Python sul runner di provisioning finché PyYAML non supporta 3.15.
