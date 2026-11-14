# ADR 0142 — L'avvio di un flusso fermo verifica il capitale libero come quello della bozza

- Stato: proposta (14 novembre 2026)
- Requisiti: Bug sull'avvio di un flusso fermo (R1.1.2, RF-02.05; scenario «Comando rifiutato» di R2.3.4)
- Collegate: ADR 0124 (avvio della bozza con verifica del capitale libero), ADR 0079

## Contesto e problema

`ChangeFlowStatusUseCase` verifica conto, asset liberi e capitale libero solo quando avvia una bozza. Un flusso fermo
tiene il suo capitale sul conto, ma il saldo può essere sceso nel frattempo: riavviarlo senza verifica può
mettere a rischio più capitale di quello che il conto ha libero, contro RF-02.05.

## Decisione

- L'azione `start` su un flusso fermo esegue la stessa verifica del capitale della bozza: capitale allocato del flusso
  entro il capitale libero del conto letto ora, escluso il flusso stesso; rifiuto con
  `CapitalAboveFreeCapitalError` (422) e il suo motivo.
- Pausa e ripresa non cambiano: il flusso in pausa è già in uso e non chiede nuovo capitale.
- Nessuna regola nuova: si riusa `FreeCapital.of_account(...).require_room_for(...)` già usato per la bozza.

## Alternative scartate

- **Verifica solo nella dashboard**: lo scenario passerebbe, ma l'API resterebbe senza la regola (tech-dashboard.md).
- **Verifica anche alla ripresa**: più severa, ma nessun requisito la chiede e bloccherebbe flussi già in uso.

## Conseguenze

- Il finto MSW di R2.3.4 e l'API reale rispondono allo stesso modo.
