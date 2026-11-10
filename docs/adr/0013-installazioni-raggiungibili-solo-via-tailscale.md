# ADR 0013 — Installazioni raggiungibili solo dal tailnet Tailscale

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.5.2, R0.5.3, R0.5.4
- Sostituisce: ADR 0012; le parti "Segreti e variabili" (chiavi SSH), "Firewall" e "Indirizzo" dell'ADR 0008

## Contesto

Il progetto OVH ha quota 0 per security group e regole, e il gruppo `default` non ha più regole in
ingresso: rifiuta ogni connessione da Internet e lascia uscire la macchina. OVH rifiuta una porta
pubblica senza security group (`create_port:port_security_enabled is disallowed by policy`). Un nuovo
progetto o una rete privata con IP pubblico costano, e il proprietario lo esclude.

## Decisione

- Le installazioni non accettano connessioni da Internet. Si raggiungono solo dal **tailnet Tailscale**
  del proprietario: la macchina apre lei la connessione in uscita, quindi il gruppo `default` resta
  così com'è e nessun security group o regola viene creato, modificato o eliminato.
- **Accesso amministrativo**: Tailscale SSH, solo come utente `deploy`. Niente chiavi SSH; `sshd` spento.
  La pipeline entra con `accept`, i dispositivi del proprietario con `check` (nuovo login periodico).
- **HTTPS**: Tailscale Serve su `https://autotrading-<ambiente>.<tailnet>.ts.net`, certificato gestito da
  Tailscale, verso l'API che ascolta solo su `127.0.0.1:8000`. Caddy esce dal compose.
- **Firewall sulla macchina**: `ufw` rifiuta tutto in ingresso tranne l'interfaccia `tailscale0`.
- **Pipeline senza segreti Tailscale**: una credenziale OIDC (workload identity federation) per
  environment GitHub, subject immutabile
  `repo:ElettroAle@13102057/autotrading@1448691814:environment:<ambiente>`, scope `auth_keys`, tag
  `tag:ci` e `tag:autotrading-<ambiente>`. Client ID e Audience sono variabili dell'environment
  (`TS_CLIENT_ID`, `TS_AUDIENCE`).
- **`provision`**: con l'identità del job crea una chiave monouso, preautorizzata, valida un'ora, con il
  solo tag `tag:autotrading-<ambiente>`; cloud-init la usa per far entrare la macchina nel tailnet.
- **Job di provision e rilascio**: entrano nel tailnet con l'action ufficiale `tailscale/github-action`
  come nodi temporanei `tag:ci`; trovano la macchina per nome, senza credenziali OVH nel rilascio.
- **Policy del tailnet**: versionata in `deploy/tailscale/policy.hujson`, applicata a mano dal
  proprietario. Ogni tag è proprietario di sé stesso, perché una credenziale con due tag possa dare un
  solo tag per chiave.

## Alternative scartate

- **Policy e credenziali applicate dalla pipeline** (credenziale con `Policy File: Write` e
  `Federated Keys: Write`): una policy alterata potrebbe aprire alla pipeline i dispositivi personali
  del proprietario.
- **SSH classico sul tailnet con chiavi**: quattro credenziali da custodire in più, senza vantaggi.
- **Tailscale Funnel (accesso pubblico)**: espone la pagina di login a Internet, limiti di banda.
- **Ticket a OVH, nuovo progetto, rete privata con IP pubblico**: tempi non prevedibili o costo.

## Conseguenze

- Se Tailscale non è raggiungibile, pipeline e proprietario non raggiungono le installazioni.
- Per vedere la dashboard serve l'app Tailscale sul dispositivo, collegata al tailnet.
- Il nome della macchina va liberato nel tailnet quando la si ricrea, altrimenti diventa
  `autotrading-<ambiente>-1` e il rilascio non la trova.
- I segreti e le variabili delle chiavi SSH (`DEPLOY_SSH_*`, `HOST_SSH_*`) non servono più.
- Il piano gratuito Tailscale (Personal) è per uso non commerciale: va rivisto se AutoTrading diventa un
  servizio venduto.
- La regione predefinita è `SBG5`: il 10 novembre 2026 `GRA11` non aveva capacità per `d2-2` (`No valid host
  was found`). Il listino OVH ha un solo prezzo per `d2-2`, valido per ogni regione.
- Il nome `.ts.net` della macchina compare nei registri pubblici dei certificati; non dà accesso.
