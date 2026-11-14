# ADR 0131 — Editor della configurazione del flusso guidato dai cataloghi dell'API

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.3.3 (Task T2.3.3.1)
- Collegate: ADR 0116, ADR 0119, ADR 0130 (Problem Details sui campi); API `POST /flows`, `PATCH /flows/{id}`,
  `PUT /flows/{id}/allocated-capital`, `GET /models`, `GET /sources`

## Contesto e problema

Il flusso si configura con asset, intervallo, fonti con pesi e parametri, modello con parametri, istruzioni,
limiti di rischio e capitale. I parametri ammessi di fonti e modelli li dichiarano i cataloghi dell'API.

## Decisione

- Funzionalità `flow-editor` con un solo form React Hook Form; le sezioni fonti e modello costruiscono i campi dei
  parametri dalla descrizione dei cataloghi (`GET /sources/{name}`, `GET /models`), senza elenchi scritti nel
  codice della dashboard.
- Creazione con `POST /flows`; modifica con `PATCH /flows/{id}` dei soli campi cambiati; il capitale con il suo
  endpoint dedicato.
- Errori dell'API sui campi con il modulo di ADR 0130.

## Alternative scartate

- **Form a passi (wizard)**: guida l'utente, ma la modifica di un solo campo diventa lunga.
- **Campi dei parametri scritti a mano per fonte e modello**: semplice, ma diverge al primo catalogo che cambia.

## Conseguenze

- Una fonte o un modello nuovi nel catalogo compaiono nell'editor senza cambiare la dashboard.
