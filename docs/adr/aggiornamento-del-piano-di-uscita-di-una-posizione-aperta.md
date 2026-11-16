# ADR aggiornamento-del-piano-di-uscita-di-una-posizione-aperta — Aggiornamento di stop e obiettivo di una posizione aperta

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.1.3 (456), Task T3.1.3.1 (476); R1.5.3
- Collegate: ADR piano-di-uscita-nella-decisione-dell-agente, ADR ordini-di-protezione-sull-exchange, ADR
  risposta-del-modello-con-schema-rigido

## Contesto e problema

L'agente può aprire, chiudere o mantenere (`TradeAction`): per spostare lo stop di una posizione deve chiuderla.
R3.1.3 chiede un'azione che aggiorna il piano di uscita (nuovo stop, nuovo obiettivo, nuova invalidazione, obiettivo
tolto) e sostituisce le protezioni sull'exchange, con lo stop mai tolto e mai oltre il predefinito, i livelli
incoerenti scartati, il rifiuto dell'exchange che lascia l'ordine precedente, e il prima e dopo registrati.

## Fattori decisionali

- Decisioni del proprietario (16/11/2026, piano di E3): l'agente può spostare lo stop mai oltre il predefinito del
  flusso e mai toglierlo.
- R1.5.3: una decisione incoerente con lo stato del flusso si blocca col motivo, le altre proseguono.
- CLAUDE.md: il caso d'uso orchestra; regole nel domain.

## Opzioni considerate

1. `TradeAction.UPDATE = "aggiorna"`; la voce della risposta con azione `aggiorna` usa le chiavi del piano
   (`obiettivo`, `stop`, `invalidazione`) e una chiave `togli_obiettivo` (booleana, nello schema rigido): `null` vuol
   dire «resta quello in vigore». `Decision.intent_with` produce un `UpdateIntent(asset, plan_change)`. Il controllo
   del rischio blocca un `UpdateIntent` senza posizione aperta con «nessuna posizione aperta su <asset>»
   (`BlockedDecision`), scarta i livelli incoerenti col prezzo di mercato (stessa regola di `ExitPlan` e stesse note)
   e approva un `ApprovedUpdate(asset, plan_change)`, che `order_with` (con un terzo costruttore) porta
   all'esecuzione come `FlowUpdate` (`domain/orders/flow_order.py`), inviato dopo le chiusure e prima delle aperture.
   `UpdateFlowProtectionUseCase` (`application/orders/update_flow_protection.py`) legge le protezioni registrate,
   calcola lo stop nuovo con la stessa `ProtectionRequest` (riportato al predefinito sul prezzo d'ingresso della
   posizione, con la nota), piazza il nuovo ordine e solo dopo annulla il precedente, così resta sempre uno stop; un
   rifiuto lascia l'ordine precedente e la nota `"stop <asset> non aggiornato, <motivo>"`; obiettivo tolto annulla il
   take profit. Nota del cambio `"stop <asset> da <prima> a <dopo>"` (e `obiettivo` allo stesso modo) nel documento
   del passo «esecuzione degli ordini». Il piano in vigore (`ExitPlanRepositoryPort`) si aggiorna solo con i livelli
   davvero piazzati. Il system prompt predefinito descrive l'azione nuova.
2. Aggiornamento come chiusura e riapertura: scartato, costi e slippage inutili e perdita del prezzo d'ingresso.

## Esito della decisione

Opzione 1.

Verifica: prova (scenari di R3.1.3 con adapter finti; unit test di intent, controllo del rischio e caso d'uso).

### Conseguenze

- Per posizione restano sempre un solo stop loss e al più un take profit; il piano che torna all'agente è quello
  piazzato.
