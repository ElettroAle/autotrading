# ADR 0010 — Firewall OVH sul security group default del progetto

- Stato: sostituita dall'ADR 0012 (10 novembre 2026)
- Requisiti: R0.5.4
- Sostituisce: la sola parte "Firewall" dell'ADR 0008

## Contesto

Il primo provisioning di `dev` si è fermato alla creazione del security group `autotrading-dev`:
`Quota exceeded for resources: ['security_group']`. Il progetto nuovo ha già esaurito la quota dei
security group con il gruppo `default`, che OVH crea da solo e che accetta qualunque connessione.
Il livello di quota successivo si ottiene solo aggiungendo credito al progetto (da 119,50 USD in
su), escluso dal proprietario.

## Decisione

- La pipeline usa il security group **`default`** del progetto: ne elimina ogni regola in ingresso
  che non sia TCP 22 o TCP 443 e aggiunge, se mancano, le regole TCP 22 e 443 per IPv4 e IPv6. Le
  regole in uscita restano.
- L'operazione è idempotente e si ripete a ogni esecuzione di `provision` che crea la macchina.
- La macchina si crea con `--security-group default`; `ufw` sulla macchina resta.

## Alternative scartate

- **Aumentare la quota**: richiede credito aggiuntivo sul progetto.
- **Nessun security group, solo `ufw`**: le porte pubblicate da Docker scavalcano `ufw`, quindi
  l'unica barriera davanti a un `ports:` aggiunto per errore al compose sarebbe la revisione.

## Conseguenze

- OVH sconsiglia di modificare il gruppo `default`: il rischio è contenuto perché il progetto
  ospita solo AutoTrading, e ogni altra macchina creata nel progetto riceverebbe le stesse regole.
- Se in futuro la quota lo permetterà, si potrà tornare a un gruppo dedicato per installazione.
