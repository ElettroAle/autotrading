# ADR 0009 — Zona IAM dell'account OVH configurabile

- Stato: accettata (9 novembre 2026)
- Requisiti: R0.5.2, R0.5.3, R0.5.4
- Completa: ADR 0008

## Contesto

L'ADR 0008 fissa l'identity provider `ovhcloud-emea`, valido per gli account della zona europea.
L'account OVH del proprietario è stato creato dal sito internazionale (`ovhcloud.com/en`), che
appartiene alla zona canadese: il suo service account si autentica con l'identity provider
`ovhcloud-world` e il servizio IAM `iam.ovh.ca`. Il proprietario resta per ora su questo account e
prevede di passare in seguito a un account della zona europea.

## Decisione

- Variabile `OVH_ZONE` per environment, valori `eu` (predefinito) o `ca`. `ovh-setup` ne ricava
  identity provider e indirizzo di scoperta IAM; un valore diverso fa fallire l'esecuzione.
- L'environment `dev` usa `ca` finché l'account resta nella zona canadese.
- Le macchine restano in una regione europea (`OVH_REGION`, predefinita `GRA11`) qualunque sia la
  zona dell'account.

## Alternative scartate

- **Sostituire `ovhcloud-emea` con `ovhcloud-world`**: la migrazione prevista alla zona europea
  richiederebbe di nuovo una modifica al codice.
- **Due variabili libere per identity provider e indirizzo IAM**: due valori da tenere coerenti a
  mano, senza controllo.

## Conseguenze

- Il passaggio alla zona europea richiede un nuovo account, un nuovo progetto e un nuovo service
  account, poi l'aggiornamento di `OVH_ZONE`, `OVH_PROJECT_ID`, `OVH_CLIENT_ID` e
  `OVH_CLIENT_SECRET` e una nuova esecuzione di `provision`; nessuna modifica al codice.
- Un account della zona canadese fattura dalla società canadese di OVHcloud, con valuta e trattamento
  fiscale diversi da quelli europei.
