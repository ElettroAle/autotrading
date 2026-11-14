# ADR 0153 — Campo di scelta da elenco condiviso nella dashboard

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.3.8 (Task 271)
- Collegate: ADR 0147 (`AssetPicker`), ADR 0151 (tendina del modello per fornitore), ADR 0146 (campi entro la
  larghezza), ADR 0152 (`GET /exchanges`)

## Contesto e problema

Exchange del conto e fornitore della chiave IA sono campi di testo libero; vanno scelti da elenchi dell'API, come asset
e modello, centralizzando dove possibile. Exchange e fornitore sono scelte singole da elenchi brevi, con opzioni che
possono essere non selezionabili (fornitore già registrato) e un elenco che può non essere disponibile; la tendina del
modello (ADR 0151) è già una scelta singola nativa con gruppi e opzioni disabilitate. `AssetPicker` è invece una scelta
multipla con ricerca.

## Fattori decisionali

- `tech-dashboard.md`: bulletproof-react; codice condiviso in `src/components` e `src/hooks`, nessun import tra
  funzionalità.
- ADR 0116: elenchi solo dall'API.
- ADR 0146: campi entro la larghezza del telefono; ADR 0151: `<select>` nativo per accessibilità e telefono.
- Richiesta del proprietario: elenchi come per gli asset, centralizzando ove possibile.

## Opzioni considerate

### 1. `SelectField` condiviso a scelta singola, usato da exchange, fornitore e modello

- Pro: un solo componente per le scelte singole (stato vuoto, caricamento, elenco non disponibile, opzioni e gruppi
  disabilitati); la tendina del modello ci passa sopra senza cambiare comportamento.
- Contro: `AssetPicker` resta a sé.

### 2. Generalizzare `AssetPicker` anche alle scelte singole

- Pro: un solo componente per tutti gli elenchi.
- Contro: ricerca ed etichette rimovibili non servono a elenchi di poche voci; interazione più lenta da telefono.

## Esito della decisione

Opzione 1. `src/components/ui/form/select-field.tsx` esporta `SelectField`: `<select>` nativo dentro `FormField`, con
opzioni o gruppi di opzioni (`label`, `value`, `disabled`, nota), segnaposto, stato di caricamento e messaggio di elenco
non disponibile che rende il campo non utilizzabile e blocca l'invio del modulo. Lo usano: l'exchange della
registrazione del conto, con l'elenco da `useSupportedExchanges` in `src/hooks` su `GET /exchanges`; il fornitore della
registrazione di una chiave IA, con i `providers` del catalogo (`GET /models`) e quelli già registrati disabilitati con
la nota «chiave già registrata»; la tendina del modello del flusso (ADR 0151), che passa a `SelectField` con gli stessi
gruppi. `AssetPicker` resta la scelta multipla e condivide già `FormField` e lo stile dei campi.

Verifica: revisione.

### Conseguenze

- Una nuova scelta singola da elenco nella dashboard usa `SelectField`, senza un altro componente.
