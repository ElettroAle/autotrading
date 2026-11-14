# ADR 0124 — Il flusso in bozza: strategia senza conto, capitale né asset, avviabile dopo l'assegnazione

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.4.1 (Task T2.4.1.1); base di R2.5.2
- Collegate: R1.1.1 (creazione del flusso con conto), R1.1.2 (avvio e RF-02.05), ADR del ciclo di vita dei flussi
  (E1), CLAUDE.md «Struttura» (contesto `flows`)

## Contesto e problema

Il proprietario ha deciso (intervista di E2) che duplicazione e importazione creano un flusso in **bozza**: c'è
solo la strategia, conto, capitale e asset si assegnano prima dell'avvio, e l'avvio verifica RF-02.05. Oggi un
flusso nasce sempre con conto e capitale.

## Decisione

- Nuovo stato `bozza` nella macchina degli stati del dominio `flows`: da bozza si va solo ad attivo (avvio) o ad
  archiviato. Una bozza non esegue cicli, non impegna capitale e non conta nei conflitti di asset.
- Conto, capitale allocato e asset diventano facoltativi solo per la bozza; un invariante del dominio li richiede
  in ogni altro stato. Migrazione: colonne annullabili con un vincolo che le esige fuori dalla bozza.
- Casi d'uso del contesto `flows`: `DuplicateFlowUseCase` (copia la strategia dell'ultima versione: fonti e pesi,
  modello e parametri, istruzioni, rischio, intervallo), `AssignDraftFlowUseCase` (conto, capitale, asset; nuova
  versione della configurazione), e l'avvio esistente che, per una bozza, verifica conto, capitale, almeno un
  asset e RF-02.05 prima di portarla ad attivo.
- API: `POST /flows/{flow_id}/duplicate`, `PUT /flows/{flow_id}/assignment`; l'avvio resta l'azione esistente.

## Alternative scartate

- **Copia con il conto scelto subito**: scartata dal proprietario.
- **Bozza fuori dal flusso (tabella di modelli di strategia)**: separa i concetti, ma duplica la configurazione
  versionata e la sua validazione.

## Conseguenze

- L'importazione (R2.5.2) crea una bozza con lo stesso caso d'uso di assegnazione.
- I riepiloghi e la classifica escludono le bozze.
