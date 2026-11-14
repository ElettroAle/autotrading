# ADR 0150 — Installazione senza il container litellm

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: Bug 255 (Task 257)
- Collegate: ADR 0148, ADR 0149, ADR 0101 (sostituita), ADR 0015 (segreti generati sulla macchina)

## Contesto e problema

Con la libreria nel worker (ADR 0148) e il catalogo letto dal worker (ADR 0149), il container `litellm`, la sua
configurazione, la chiave master e i passi della pipeline che li applicano non servono più.

## Fattori decisionali

- `CLAUDE.md`: il deploy passa sempre dalla pipeline.
- ADR 0015: i segreti si generano sulla macchina.

## Opzioni considerate

### 1. Rimozione completa nella stessa PR del codice

- Pro: nessuna configurazione morta; codice e installazione cambiano insieme.
- Contro: PR più grande.

### 2. Container spento ma lasciato nel compose

- Pro: ritorno indietro immediato.
- Contro: configurazione e segreti morti da mantenere.

## Esito della decisione

Opzione 1. Escono da `deploy/compose.yaml` il servizio `litellm`, i segreti `litellm_master_key` e `litellm_config`, le
variabili `LITELLM_URL` e `LITELLM_MASTER_KEY_FILE` di api e worker e le loro dipendenze dal servizio. Escono
`deploy/litellm/`, la generazione della chiave master in `prepare-installation.sh` e i passi del rilascio che copiano la
configurazione. Il rilascio usa `--remove-orphans`, che ferma il container rimasto, e rimuove i file
`secrets/litellm_*` rimasti sulla macchina. Stessa PR dei Task 256 e 266.

Verifica: revisione.

### Conseguenze

- Un servizio e un segreto generato in meno su ogni installazione.
