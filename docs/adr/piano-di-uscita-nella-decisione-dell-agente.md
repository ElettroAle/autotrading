# ADR piano-di-uscita-nella-decisione-dell-agente — Piano di uscita nella decisione, nel contesto e nella registrazione

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.1 (454), Task T3.1.1.1 (471)
- Collegate: ADR risposta-del-modello-con-schema-rigido, ADR prezzo-di-mercato-dichiarato-dall-exchange, ADR 0038
  (contesto e risposta dell'agente nel domain), ADR system-prompt-del-flusso-come-modello-con-segnaposti

## Contesto e problema

La decisione dell'agente (`domain/agent/decision.py`) ha asset, azione, direzione, quota, leva e ragionamento: non
dice come intende uscire. R3.1.1 chiede obiettivo, stop e condizione di invalidazione facoltativi, controllati sulla
direzione rispetto al prezzo di mercato dell'exchange del conto, registrati con la decisione e riportati all'agente
finché la posizione è aperta. R3.1.2 e R3.1.3 usano lo stesso piano per gli ordini sull'exchange.

## Fattori decisionali

- Decisioni del proprietario (16/11/2026, piano di E3): stop loss predefinito obbligatorio al 5% dal prezzo d'ingresso, anche per i flussi esistenti; take profit facoltativo; l'agente può spostare lo stop mai oltre il predefinito e mai toglierlo.
- ADR risposta-del-modello-con-schema-rigido: lo schema JSON della risposta è rigido; ogni campo è dichiarato.
- ADR prezzo-di-mercato-dichiarato-dall-exchange: il riferimento di prezzo è quello dell'exchange del conto, mai
  quello delle fonti.
- CLAUDE.md: regole nel domain, nessun testo di tecnologia o exchange in domain/application.

## Opzioni considerate

1. Value object `ExitPlan(target: Decimal | None, stop: Decimal | None, invalidation: str | None)` in
   `domain/agent/exit_plan.py`; `TradeOpening` lo porta. `agent_response.py` legge i campi `obiettivo`,
   `stop`, `invalidazione` (numeri positivi o `null`, testo o `null`); `answer_format.py` li dichiara
   nello schema rigido come nullabili e obbligatori come chiave (lo schema rigido vuole tutte le chiavi). Un numero
   non positivo o di tipo sbagliato rende la voce non conforme (R1.4.5).
   La coerenza con la direzione è una regola del domain dei flussi: `OpenIntent` porta il piano;
   `ExitPlan.coherent_with(side, market_price)` restituisce il piano senza i livelli incoerenti e le note
   `"<livello> <prezzo> scartato: incoerente con <direzione> al prezzo <prezzo>"` (long: stop >= prezzo o obiettivo
   <= prezzo incoerenti; short il contrario). Il prezzo è il `mid_price` del `Market` dell'exchange del conto:
   `AssetLimits` lo riceve dalla stessa lettura del mercato che dà leva massima e valore minimo, così il controllo
   del rischio (`RiskCheck._open`) applica la regola e mette le note tra le `Adjustment` dell'apertura
   approvata (nuovo `AdjustmentKind.EXIT_PLAN`), registrate nel documento del passo «controllo del rischio».
   Il piano approvato viaggia su `ApprovedOpening` e sul `FlowOpening` fino all'esecuzione (R3.1.2).
   Il piano in vigore di una posizione aperta si conserva per flusso e asset: porta `ExitPlanRepositoryPort` in
   `application/flows/ports.py` (`current(flow_id, asset)`, `save(flow_id, asset, plan)`, `remove(flow_id,
   asset)`), realizzata in `adapters/outbound/sqlalchemy/` con tabella `flow_exit_plans` (tenant, RLS,
   migrazione Alembic) e `InMemoryExitPlanRepositoryAdapter` nei test. Si salva dopo un'apertura eseguita, si
   toglie alla chiusura della posizione (agente, manuale, stop del flusso, fuori piattaforma, protezione).
   `PositionView` (`flow_state_view.py`) e la posizione del contesto ricevono il piano in vigore: lo stato del
   flusso inviato all'agente lo riporta per posizione (obiettivo, stop, invalidazione) e il system prompt predefinito
   descrive i nuovi campi della risposta. La decisione registrata (documento del passo «decisione dell'agente»)
   contiene il piano come lo ha dato l'agente; l'API del dettaglio del ciclo e delle posizioni aperte espone i
   livelli.
2. Piano ricostruito a ogni ciclo dall'ultima decisione registrata: scartato, lega la lettura al formato dei documenti
   del ciclo e non regge l'aggiornamento di R3.1.3 né le chiusure fuori dal ciclo.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.1.1 sui casi d'uso con adapter finti; unit test di `ExitPlan`, lettura della
risposta, schema; test di integrazione del repository su PostgreSQL).

### Conseguenze

- R3.1.2 e R3.1.3 lavorano su un piano già validato e conservato.
- Lo schema della risposta cresce di tre chiavi; i modelli che rispondono senza di esse danno voci non conformi.
