# ADR 0011 — Firewall OVH: ingresso solo IPv4

- Stato: accettata (9 novembre 2026)
- Requisiti: R0.5.4
- Sostituisce: le regole IPv6 in ingresso dell'ADR 0010

## Contesto

Il secondo provisioning di `dev` si è fermato con `Quota exceeded for resources:
['security_group_rule']`: il progetto ammette pochissime regole, e il gruppo `default` ne usa già due
in uscita. Le quattro regole in ingresso dell'ADR 0010 (TCP 22 e 443 per IPv4 e IPv6) non ci stanno.

## Decisione

- Nel gruppo `default` restano in ingresso solo TCP 22 e TCP 443 **per IPv4**; ogni altra regola in
  ingresso, comprese quelle IPv6, si elimina. Le regole in uscita restano.
- Se la creazione di una regola fallisce, la pipeline stampa le regole del gruppo e, se il service
  account può leggerle, le quote di rete del progetto.

## Alternative scartate

- **Aumentare la quota**: richiede credito aggiuntivo sul progetto.
- **Eliminare le regole in uscita per far posto all'IPv6**: la macchina non potrebbe più scaricare
  immagini e aggiornamenti.

## Conseguenze

- Il nome pubblico `<ip-con-trattini>.sslip.io` usa l'indirizzo IPv4, quindi nessun servizio
  dipende dall'IPv6 in ingresso. Senza regole IPv6 in ingresso, il traffico IPv6 dall'esterno è
  rifiutato: più restrittivo di prima.
