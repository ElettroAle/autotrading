# ADR limite-di-esposizione-tolto-con-un-null-inviato-apposta — Limite di esposizione tolto con un null inviato apposta

- Stato: proposta (16 novembre 2026)
- Requisiti: Bug 503, Task 504; R1.1.1, R1.1.3, R1.5.1, R2.3.3
- Collegate: ADR riga-del-system-prompt-nel-confronto-delle-versioni, ADR system-prompt-del-flusso-come-modello-con-segnaposti (R1.4.8)

## Contesto e problema

Nella modifica del flusso un limite di esposizione a `null` vuol dire «resta quello in vigore»
(`ModifyFlowRequest`, `ModifyFlowCommand`, `_risk_limits` in `modify_flow.py`). La dashboard manda `null` per il
campo svuotato (`decimalOrNull` in `flow-form.ts`): una volta impostato, un limite si può cambiare ma non togliere.

## Fattori decisionali

- R1.1.3: la modifica salva la nuova versione con i valori scelti; un limite svuotato va tolto.
- R1.1.1: serve almeno un limite di esposizione. La regola esiste già nel domain (`RiskLimits.__post_init__`,
  `ExposureLimitRequiredError`) e non si duplica.
- R1.4.8: il system prompt distingue già il `null` inviato apposta dal campo assente, con `model_fields_set` nella
  richiesta FastAPI e un flag esplicito nel comando (`default_system_prompt`). Si segue la stessa via.
- CLAUDE.md: il caso d'uso orchestra, l'adapter traduce soltanto; nessuna regola di business nell'adapter.

## Opzioni considerate

1. Come per il system prompt: `ModifyFlowRequest` passa al comando due flag, `remove_max_margin_exposure` e
   `remove_max_value_exposure`, veri quando il campo è in `model_fields_set` con valore `null`. `_risk_limits`
   toglie il limite col flag vero, tiene quello in vigore col campo assente, usa il valore inviato altrimenti.
   `RiskLimits` rifiuta la combinazione senza limiti con `ExposureLimitRequiredError` (422, motivo «almeno un limite
   di esposizione è obbligatorio»). La dashboard continua a mandare `null` per il campo svuotato.
2. Un valore sentinella (per esempio `0`) per dire «togli»: scartata, `0` è un valore di dominio e confonde.
3. La modifica manda sempre la configurazione completa: scartata, cambia il contratto PATCH e tutti i client.

## Esito della decisione

Opzione 1. I flag si chiamano come l'azione (`remove_*`), sul modello di `default_system_prompt`.

Verifica: prova (scenari del Bug 503 sul caso d'uso, test dell'API con campo `null` e campo assente, unit test di
`_risk_limits` e del modulo della dashboard che svuota un limite).

### Conseguenze

- Un limite svuotato sparisce dalla nuova versione e il confronto delle versioni lo mostra tolto.
- Un client che manda `null` per un limite che non vuole cambiare ora lo toglie: la dashboard è l'unico client e
  manda già i valori in vigore per i campi non toccati.
