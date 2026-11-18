# ADR api-degli-avvisi-e-link-nelle-notifiche — API degli avvisi e notifiche che aprono il dettaglio

- Stato: proposta (18 novembre 2026)
- Requisiti: R6.2.3, Task 608; R3.5.6
- Collegate: ADR avvisi-nel-contesto-delle-notifiche, ADR destinazioni-delle-notifiche-nella-dashboard, ADR 0027
  (Problem Details), ADR 0074 (keyset)
- Verifica: prova

## Contesto e problema

La pagina Avvisi e il numero nel menu leggono gli avvisi dall'API; la notifica di un avviso deve aprirne il dettaglio
invece della pagina della risorsa.

## Fattori decisionali

- Una sola risposta per errore (Problem Details), porte legate al tenant.
- Le rotte della dashboard le conosce solo `adapters/outbound/dashboard/`.

## Decisione

- API (`adapters/inbound/api/alerts.py`):
  - `GET /alerts` con `state` (`open`, `resolved`, `all`; predefinito `open`), `severity`, `resource_kind`,
    `resource_id`, `since`, `until`, `cursor`: pagine di 50 dalla più recente;
  - `GET /alerts/summary`: `open_count`;
  - `GET /alerts/{id}`: dettaglio con valori e comandi ammessi (`confirm_reconciliation`, `resume_flow`, `resolve`);
  - `POST /alerts/{id}/resolution`: solo per i generi a mano; 409 altrimenti, 404 se non è del tenant.
  I comandi di conferma e ripresa restano gli endpoint esistenti.
- Link: `NotificationTarget` aggiunge il genere `ALERT` con l'id dell'avviso; le notifiche dei quattro eventi portano
  il target dell'avviso aperto («Apri avviso») al posto di «Apri allarmi»; `DashboardNotificationLinkAdapter` lo
  traduce in `/alerts/{id}`.
- Schema OpenAPI e client generato aggiornati.
- Prove: unit test degli endpoint (filtri, 404, 409, tenant), dell'adapter delle rotte e degli scenari di R3.5.6.

## Alternative scartate

- Link alla pagina della risorsa: il dettaglio dell'avviso dice che cosa fare e porta alla risorsa.

## Conseguenze

- Ogni avviso ha un indirizzo stabile, aperto dalla notifica.
