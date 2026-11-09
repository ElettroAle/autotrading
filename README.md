# AutoTrading

AI-driven automated trading platform.

## Project tracking

- **Work items / Boards:** Azure DevOps, project [AutoTrading](https://dev.azure.com/fianialessandro/AutoTrading/_boards)
- **Code, PRs, CI/CD:** GitHub (this repository)

Link commits and pull requests to Azure Boards work items by mentioning `AB#<id>` in the commit message or PR description (for example `AB#42`).

## Installazione di un ambiente (dev o prod)

Le installazioni girano su OVH Public Cloud e le crea solo la pipeline (ADR 0008 e 0009). Nessun
segreto passa dalla chat o da file sul disco: i segreti si scrivono con `gh secret set`, che li chiede
senza mostrarli. Nei comandi sostituisci `<env>` con `dev` o `prod`.

### 1. Account e progetto OVH

1. Un account OVH con un metodo di pagamento. La zona dell'account dipende dal sito da cui è stato
   creato: `ovhcloud.com/it` (o un altro sito europeo) è la zona `eu`, `ovhcloud.com/en` è la zona
   `ca`. Il login della console API e dell'IAM rivela la zona (`eu.api.ovh.com` o `ca.api.ovh.com`).
2. Pannello OVH, **Public Cloud**: un progetto (per esempio `autotrading`). Annota il suo ID, 32
   caratteri esadecimali sotto il nome.

### 2. Service account e policy

1. Pannello OVH, **Identity, Security & Operations > Identities > Service account > Add a service
   account**, nome `autotrading-<env>`. La finestra mostra il nome (`clientId`) e la password
   (`clientSecret`): la password si vede una volta sola e non si recupera.
2. **Identity and Access Management > Policy**: una policy con identità il service account, risorsa
   **solo** il progetto Public Cloud e i permessi OpenStack per gestire istanze, rete, security group
   e keypair.

### 3. Segreti e variabili dell'environment GitHub

```
gh secret set OVH_CLIENT_ID --env <env> -R ElettroAle/autotrading
gh secret set OVH_CLIENT_SECRET --env <env> -R ElettroAle/autotrading
gh variable set OVH_PROJECT_ID --env <env> -R ElettroAle/autotrading --body <id-progetto>
gh variable set OVH_ZONE --env <env> -R ElettroAle/autotrading --body <eu|ca>
```

Facoltative: `OVH_REGION` (predefinita `GRA11`) e `OVH_FLAVOR` (predefinito `d2-2`).

### 4. Chiavi SSH

Due coppie di chiavi ed25519, generate in una cartella temporanea e cancellate subito dopo:

- utente `deploy`: privata nel segreto `DEPLOY_SSH_PRIVATE_KEY`, pubblica nella variabile
  `DEPLOY_SSH_PUBLIC_KEY`;
- chiave host della macchina: privata nel segreto `HOST_SSH_PRIVATE_KEY`, pubblica nella variabile
  `HOST_SSH_PUBLIC_KEY`.

```
gh secret set DEPLOY_SSH_PRIVATE_KEY --env <env> -R ElettroAle/autotrading < deploy
gh variable set DEPLOY_SSH_PUBLIC_KEY --env <env> -R ElettroAle/autotrading < deploy.pub
```

(e lo stesso per la chiave host), poi si cancellano i file.

### 5. Creazione e primo rilascio

1. GitHub, **Actions > provision > Run workflow**, ambiente `<env>`. Crea la macchina, il firewall
   (solo 22 e 443) e il certificato HTTPS su `<ip-con-trattini>.sslip.io`. Ripeterlo non duplica
   nulla.
2. Il rilascio parte da solo a ogni merge su `main` (dev) e con l'approvazione del proprietario
   (prod). Per il primo rilascio di un ambiente appena creato: **Actions > release**, rilancia
   l'ultima esecuzione.

## Migrazione a un altro account OVH (per esempio da zona `ca` a `eu`)

1. Sul nuovo account ripeti i passi 1 e 2 sopra.
2. Aggiorna `OVH_CLIENT_ID`, `OVH_CLIENT_SECRET`, `OVH_PROJECT_ID` e `OVH_ZONE` nell'environment
   (passo 3). Le chiavi SSH restano le stesse.
3. Lancia **provision** per l'ambiente, poi rilancia il rilascio: la nuova macchina riceve lo stesso
   artefatto (stesso digest).
4. In E0 l'installazione non conserva dati da trasferire. Quando ci saranno dati da conservare, prima
   di spegnere la vecchia macchina si esegue un `pg_dump` e lo si ripristina sulla nuova. La coppia di
   chiavi che cifra le credenziali dei conti nasce sulla macchina (ADR 0007) e non si sposta: dopo la
   migrazione le credenziali dei conti vanno reinserite.
5. Verificato `/health` sul nuovo nome pubblico, sul vecchio account elimina istanza, security group,
   keypair e progetto, così smette di fatturare.
