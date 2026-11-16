# ADR confidenza-nella-decisione-e-confidenza-minima — Confidenza nella decisione e confidenza minima del flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.4 (457), Task T3.1.4.1 (477); R1.4.5, R1.1.3
- Collegate: ADR piano-di-uscita-nella-decisione-dell-agente, ADR risposta-del-modello-con-schema-rigido, ADR
  stop-loss-e-take-profit-predefiniti-del-flusso

## Contesto e problema

La decisione non dice quanto l'agente ne è convinto. R3.1.4 chiede una confidenza intera da 0 a 100 obbligatoria in
ogni decisione (assente o fuori intervallo = non conforme), registrata e mostrata, e una confidenza minima facoltativa
del flusso che blocca solo le aperture sotto soglia.

## Fattori decisionali

- Decisioni del proprietario (16/11/2026, piano di E3) sul rischio: chiusure e aggiornamenti del piano riducono il
  rischio e si eseguono sempre.
- Bug 441: ogni parte nuova della configurazione entra anche in `domain/flows/configuration_difference.py` e in
  `dashboard/src/features/flow-versions/utils/configuration-rows.ts`; un test lega i nomi all'API.
- R2.3.3: un rifiuto nomina l'impostazione (`FlowSetting`).

## Opzioni considerate

1. `Decision.confidence: int`; `agent_response.py` legge la chiave `confidenza` (intero 0–100, altrimenti voce non
   conforme) e `answer_format.py` la dichiara obbligatoria nello schema rigido (`integer`, `minimum` 0, `maximum`
   100). La decisione registrata la contiene; le API del dettaglio del ciclo la espongono. Value object
   `MinimumConfidence` (0–100) in `domain/flows/minimum_confidence.py`, campo `minimum_confidence: MinimumConfidence |
   None` di `FlowConfiguration`, errore `InvalidMinimumConfidenceError` («la confidenza minima va da 0 a 100»),
   `FlowSetting.MINIMUM_CONFIDENCE = "minimum_confidence"`; colonna della versione con migrazione (assente per le
   versioni esistenti), API, editor, esportazione e importazione, duplicazione, confronto delle versioni. `OpenIntent`
   porta la confidenza e `RiskPolicy` la soglia: il controllo del rischio blocca un'apertura sotto soglia con
   `"apertura <asset> non eseguita: confidenza <c> sotto la minima <m>"` (`BlockedDecision`); chiusure e aggiornamenti
   non la guardano. Il system prompt predefinito descrive la chiave.
2. Confidenza facoltativa con default: scartato, R3.1.4 la vuole in ogni decisione.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.1.4; unit test di lettura della risposta, schema, value object e controllo del
rischio; test di integrazione della migrazione).

### Conseguenze

- Le risposte dei modelli senza confidenza diventano voci non conformi.
