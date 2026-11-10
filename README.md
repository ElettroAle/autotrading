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
   **solo** il progetto Public Cloud e i permessi OpenStack per gestire istanze.

### 3. Segreti e variabili dell'environment GitHub

```
gh secret set OVH_CLIENT_ID --env <env> -R ElettroAle/autotrading
gh secret set OVH_CLIENT_SECRET --env <env> -R ElettroAle/autotrading
gh variable set OVH_PROJECT_ID --env <env> -R ElettroAle/autotrading --body <id-progetto>
gh variable set OVH_ZONE --env <env> -R ElettroAle/autotrading --body <eu|ca>
```

Facoltative: `OVH_REGION` (predefinita `GRA11`) e `OVH_FLAVOR` (predefinito `d2-2`).

### 4. Tailscale (rete privata delle installazioni, ADR 0013)

Le installazioni non accettano connessioni da Internet: pipeline e proprietario le raggiungono solo dal
tailnet Tailscale. Nessuna chiave SSH e nessun segreto Tailscale.

Una volta sola per il tailnet:

1. Account gratuito su https://login.tailscale.com/start (login con GitHub).
2. https://console.tailscale.com/admin/dns: **MagicDNS** attivo e **HTTPS Certificates > Enable HTTPS**.
3. https://console.tailscale.com/admin/acls, **JSON editor**: incolla `deploy/tailscale/policy.hujson`
   e salva. Si ripete a ogni modifica di quel file.
4. App Tailscale sui dispositivi da cui aprire la dashboard, con lo stesso account.

Per ogni ambiente:

1. https://console.tailscale.com/admin/settings/trust-credentials, **Credential > OpenID Connect**:
   - Issuer **GitHub** (`https://token.actions.githubusercontent.com`);
   - Subject `repo:ElettroAle/autotrading:environment:<env>`;
   - scope **Auth Keys > Write**, tag `tag:ci` e `tag:autotrading-<env>`.
2. Client ID e Audience non sono segreti:

```
gh variable set TS_CLIENT_ID --env <env> -R ElettroAle/autotrading --body <client-id>
gh variable set TS_AUDIENCE --env <env> -R ElettroAle/autotrading --body <audience>
```

### 5. Creazione e primo rilascio

1. GitHub, **Actions > provision > Run workflow**, ambiente `<env>`. Crea la macchina con il security
   group `default` del progetto così com'è, la fa entrare nel tailnet come `autotrading-<env>` e verifica
   HTTPS su `https://autotrading-<env>.<tailnet>.ts.net`. Ripeterlo non duplica nulla.
2. Il rilascio parte da solo a ogni merge su `main` (dev) e con l'approvazione del proprietario
   (prod). Per il primo rilascio di un ambiente appena creato: **Actions > release**, rilancia
   l'ultima esecuzione.
3. Dashboard: con l'app Tailscale accesa, `https://autotrading-<env>.<tailnet>.ts.net`.

Se si ricrea la macchina, prima si elimina il vecchio dispositivo `autotrading-<env>` da
https://console.tailscale.com/admin/machines, altrimenti la nuova prende un altro nome.

## Migrazione a un altro account OVH (per esempio da zona `ca` a `eu`)

1. Sul nuovo account ripeti i passi 1 e 2 sopra.
2. Aggiorna `OVH_CLIENT_ID`, `OVH_CLIENT_SECRET`, `OVH_PROJECT_ID` e `OVH_ZONE` nell'environment
   (passo 3). Tailscale resta com'è; elimina dal tailnet il dispositivo della vecchia macchina prima
   di creare la nuova.
3. Lancia **provision** per l'ambiente, poi rilancia il rilascio: la nuova macchina riceve lo stesso
   artefatto (stesso digest).
4. In E0 l'installazione non conserva dati da trasferire. Quando ci saranno dati da conservare, prima
   di spegnere la vecchia macchina si esegue un `pg_dump` e lo si ripristina sulla nuova. La coppia di
   chiavi che cifra le credenziali dei conti nasce sulla macchina (ADR 0007) e non si sposta: dopo la
   migrazione le credenziali dei conti vanno reinserite.
5. Verificato `/health` sulla nuova macchina, sul vecchio account elimina istanza e progetto, così
   smette di fatturare.
