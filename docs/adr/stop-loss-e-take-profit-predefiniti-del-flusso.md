# ADR stop-loss-e-take-profit-predefiniti-del-flusso — Stop loss e take profit predefiniti nella configurazione del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.2 (455), Task T3.1.2.2 (474); R1.1.3
- Collegate: ADR ordini-di-protezione-sull-exchange, ADR riga-del-system-prompt-nel-confronto-delle-versioni

## Contesto e problema

`FlowConfiguration` non ha livelli di protezione. R3.1.2 chiede uno stop loss predefinito obbligatorio (da 0,1 a 50%,
5 se non indicato, 5 anche per i flussi esistenti) e un take profit predefinito facoltativo (maggiore di 0 o
assente), che creano una versione della configurazione e valgono per le aperture successive.

## Fattori decisionali

- Decisioni del proprietario (16/11/2026, piano di E3): stop loss predefinito obbligatorio al 5% dal prezzo
  d'ingresso, anche per i flussi esistenti; take profit facoltativo.
- Bug 441: ogni parte nuova della configurazione entra anche in `domain/flows/configuration_difference.py` e in
  `dashboard/src/features/flow-versions/utils/configuration-rows.ts`; un test lega i nomi all'API.
- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile
  (campi dell'editor esistenti, tabella condivisa), nessun duplicato per pagina.
- R2.3.3: un rifiuto nomina l'impostazione (`FlowSetting`).

## Opzioni considerate

1. Value object `ProtectionDefaults(stop_loss_percent: Decimal = 5, take_profit_percent: Decimal | None = None)` in
   `domain/flows/protection_defaults.py`, campo `protection_defaults` di `FlowConfiguration` (default
   `ProtectionDefaults()`); errori `InvalidDefaultStopLossError` («lo stop loss predefinito va da 0,1 a 50») e
   `InvalidDefaultTakeProfitError` («il take profit predefinito è maggiore di 0»), con `FlowSetting`
   `DEFAULT_STOP_LOSS = "default_stop_loss_percent"` e `DEFAULT_TAKE_PROFIT = "default_take_profit_percent"`.
   Persistenza: colonne della versione della configurazione, migrazione Alembic che dà 5 e assente alle versioni
   esistenti (nessuna versione nuova). API di creazione, modifica, lettura delle versioni, esportazione e importazione
   della strategia, duplicazione; editor del flusso con i due campi; righe del confronto delle versioni in
   `configuration_difference.py` e `configuration-rows.ts`; client OpenAPI rigenerato. Il ciclo passa i predefiniti
   della versione in vigore nella `ProtectionRequest` di ogni apertura.
2. Livelli dentro `RiskLimits`: scartato, i limiti di esposizione hanno regole e messaggi propri e «almeno uno dei
   due» non vale per la protezione.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.1.2 sulla configurazione; unit test del value object; test di integrazione della
migrazione).

### Conseguenze

- Ogni flusso, nuovo o esistente, ha uno stop loss predefinito.
