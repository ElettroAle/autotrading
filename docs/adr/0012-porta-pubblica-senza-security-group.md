# ADR 0012 — Porta pubblica senza security group, firewall solo ufw

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.5.4
- Sostituisce: ADR 0010 e ADR 0011

## Contesto

Il progetto OVH ha quota 0 sia per i security group sia per le regole (`security_groups` 0, in uso 1;
`security_group_rules` 0, in uso 18). Le esecuzioni dell'ADR 0010 e 0011 hanno eliminato le regole in
ingresso del gruppo `default` prima di scoprire che non se ne potevano creare di nuove: il gruppo
`default` oggi rifiuta ogni connessione in ingresso e non si può ripristinare dalla pipeline. Un nuovo
progetto richiede credito aggiuntivo, escluso dal proprietario.

## Decisione

- La pipeline non crea, non modifica e non elimina security group o regole.
- `provision` crea su `Ext-Net` una porta `autotrading-<env>-public` senza security group e con port
  security disattivata, poi crea la macchina su quella porta. Una porta lasciata da un'esecuzione
  fallita si riusa.
- L'unico firewall è `ufw` sulla macchina, attivato da cloud-init: tutto rifiutato in ingresso tranne
  TCP 22 (solo chiave, senza password, senza root) e TCP 443.
- Se OVH rifiuta la porta senza security group, `provision` si ferma prima di creare la macchina.

## Alternative scartate

- **Nuovo progetto Public Cloud**: richiede credito aggiuntivo.
- **Rete privata con router e floating IP**: circa 3,80 EUR al mese in più per lo stesso risultato.
- **Ticket a OVH per ripristinare il gruppo `default`**: tempi non prevedibili.

## Conseguenze

- Le porte pubblicate da Docker scavalcano `ufw`: il compose pubblica solo `443:443`, e ogni nuovo
  `ports:` va trattato come apertura del firewall in revisione.
- La porta 22 resta raggiungibile da Internet con accesso solo a chiave; chiuderla (rete privata tipo
  Tailscale o runner sulla macchina) è una decisione successiva.
- Il gruppo `default` resta nello stato attuale e non è usato da nessuna risorsa.
