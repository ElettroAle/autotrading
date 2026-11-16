# ADR esposizione-complessiva-nel-controllo-del-rischio — Esposizione complessiva nel controllo del rischio

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.2.1 (458), Task T3.2.1.1 (479)
- Collegate: ADR 0040 (controllo del rischio), ADR 0065 (liquidità impegnata nel ciclo), ADR 0078 (quota e limiti
  sui soldi del flusso), ADR 0051 (porta al minimo nella configurazione)

## Contesto e problema

I limiti di esposizione per operazione (R1.5.1) non impediscono che più operazioni sommate impegnino tutto il
capitale del flusso. Servono due limiti facoltativi sulla somma delle posizioni aperte del flusso, sul margine e sul
valore, in percentuale dei soldi del flusso, applicati dopo il limite per operazione; le aperture dello stesso ciclo
consumano il residuo nell'ordine di esecuzione.

## Fattori decisionali

- R3.2.1; ADR 0078: la base delle percentuali è il denaro del flusso (`RiskState.funds`).
- ADR 0065: le decisioni di un ciclo si controllano in ordine su un'unica istanza di `RiskCheck`, che già consuma
  la liquidità a ogni apertura approvata.
- R1.5.4: un residuo sotto il minimo dell'exchange segue la regola del minimo.
- R1.1.3 e Bug 441: limiti versionati e visibili nel confronto delle versioni (`configuration_difference.py` e
  `dashboard/src/features/flow-versions/utils/configuration-rows.ts`).
- Componenti riusabili dove possibile (decisione del proprietario, 16/11/2026): i campi del modulo usano i campi
  condivisi di `src/components/ui/form`, accanto ai limiti per operazione.

## Opzioni considerate

1. **Nel `RiskCheck` esistente.** `RiskLimits` aggiunge `max_total_margin_exposure_percent` e
   `max_total_value_exposure_percent` (facoltativi, da 0,1 a 1000, errore tipizzato con "l'esposizione complessiva
   massima va da 0,1 a 1000"); `RiskState` aggiunge margine e valore delle posizioni aperte del flusso, ricavati in
   `CycleFlow.risk_state()` dalle posizioni del flusso (valore = dimensione × prezzo di mercato, margine = quello
   dichiarato dall'exchange per la posizione, l'unico margine dei controlli per ADR 0067). Dopo `_within_exposure`, un passo `_within_total_exposure` riduce il valore al residuo più restrittivo
   (residuo di margine e di valore convertiti nel valore alla leva dell'apertura); un residuo nullo blocca con
   "apertura <asset> non eseguita: esposizione complessiva del <margine|valore> al <p>% esaurita". Ogni apertura
   approvata somma margine e valore all'esposizione dell'istanza, come la liquidità (ADR 0065).
2. Un controllo separato dopo il `RiskCheck`: scartato, dovrebbe rifare la regola del minimo e l'ordine delle
   aperture, già nel `RiskCheck`.

## Esito della decisione

Opzione 1.

- La riduzione è un `Adjustment` di tipo nuovo (margine complessivo, valore complessivo) con motivo "esposizione
  complessiva del margine al 30%"; il registro del ciclo lo scrive come le altre riduzioni: "apertura BTC ridotta
  da 150 a 100 USDC di margine: esposizione complessiva del margine al 30%".
- Configurazione: le due chiavi nel documento `risk_limits` della versione come `NotRequired` (assenti = nessun
  limite), senza migrazione; voci `FlowSetting.MAX_TOTAL_MARGIN_EXPOSURE` e `MAX_TOTAL_VALUE_EXPOSURE`; parti
  "esposizione complessiva massima del margine" e "esposizione complessiva massima del valore" nel confronto delle
  versioni.
- Casi d'uso, API (richieste, `RiskLimitsResponse`), documento della strategia, client OpenAPI, modulo del flusso
  e righe del confronto delle versioni portano i due campi come i limiti per operazione.

Verifica: prova (scenari di R3.2.1 sul controllo del rischio del ciclo con adapter finti, unit test di
`RiskLimits`, `RiskCheck` e `CycleFlow.risk_state`, test del modulo nella dashboard).

### Conseguenze

- Il limite complessivo usa lo stesso stato letto all'inizio del ciclo; una chiusura nello stesso ciclo non libera
  esposizione prima di essere eseguita, come per la liquidità.
