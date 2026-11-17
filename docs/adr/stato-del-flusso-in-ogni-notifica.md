# ADR stato-del-flusso-in-ogni-notifica — Stato del flusso in ogni notifica di un flusso

- Stato: proposta (17 novembre 2026)
- Requisiti: R3.5.4 (533), Task T3.5.4.2 (535)
- Collegate: ADR notifica-strutturata-con-icona-titolo-e-valori, ADR 0120 (l'equity di ogni ciclo si registra), ADR
  rendimento-composto-tra-le-variazioni-di-capitale, ADR incasso-dei-profitti, ADR 0092

## Contesto e problema

R3.5.4 chiede, in fondo a ogni notifica di un flusso, la riga «Flusso: 312,40 USDC · PnL +12,40 USDC · 2 posizioni
aperte · attivo»: valore del flusso, PnL dall'avvio, posizioni aperte e stato. Le notifiche partono dai casi d'uso
`Notify<Evento>UseCase` del contesto `notifications`, chiamati dai casi d'uso di `flows` con il nome del flusso e i
valori dell'evento. Serve decidere chi legge lo stato e con quali numeri, senza ponti tra contesti.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): lo stato del flusso «in ogni notifica» di un flusso.
- `CLAUDE.md`, niente ponti tra contesti: il contesto che usa un dato di un altro dichiara le sue porte nel proprio
  `ports.py` e l'adapter della tecnologia che ha il dato le realizza; un adapter non orchestra e non riceve casi
  d'uso; le regole sui valori stanno nel domain.
- ADR incasso-dei-profitti: valore del flusso = capitale allocato + PnL netto − incassi. ADR 0120: ogni ciclo
  registra l'equity del flusso.
- R1.8.2: una notifica non rallenta né fa fallire il ciclo, quindi niente letture dall'exchange per notificare.

## Opzioni considerate

1. **Porta del contesto `notifications`, realizzata da SQLAlchemy.**
   - `application/notifications/ports.py` dichiara `FlowStatusPort.status_of(flow_name: str) -> FlowStatusFigures |
     None`. `FlowStatusFigures` sta nel domain di `notifications`: equity dell'ultimo ciclo registrato, capitale
     allocato, incassi totali, posizioni aperte, stato, valuta.
   - `SqlAlchemyFlowStatusAdapter`, in `adapters/outbound/sqlalchemy/`, la realizza leggendo nel tenant (RLS): il
     flusso non archiviato con quel nome (il nome è unico tra i flussi non archiviati, ADR 0031), l'ultima riga di
     `equity_snapshots`, il capitale allocato, la somma degli incassi da `capital_changes` e le posizioni aperte del
     registro.
   - Il domain calcola la riga con `FlowStatusLine.of(figures)`: valore = equity; PnL dall'avvio = equity − capitale
     allocato + incassi; stato nelle parole della dashboard («attivo», «in pausa», «fermato»). Senza equity
     registrata, cioè un flusso mai girato, la riga dice «valore non disponibile»: nessun numero inventato.
   - Ogni `Notify<Evento>UseCase` di un flusso legge lo stato e lo mette nella notifica. Se la lettura fallisce, la
     notifica parte senza la riga dello stato e l'errore si registra.
2. Stato passato dai casi d'uso di `flows` a ogni porta `*NoticePort`: scartata, aggiunge quattro parametri a ogni
   porta e obbliga a leggerlo anche i chiamanti che non lo hanno a portata.
3. Lettura dello stato dall'exchange al momento della notifica: scartata, una chiamata esterna per notifica rallenta
   il ciclo e può fallire.

## Esito della decisione

Opzione 1. Il valore è quello dell'ultimo ciclo registrato, lo stesso che la dashboard mostra nel grafico: la riga
non promette un valore al secondo. Le notifiche del conto e la prova non leggono lo stato.

Verifica: prova (unit test di `FlowStatusLine`; scenari di R3.5.4 con un `FlowStatusPort` finto; test di
integrazione di `SqlAlchemyFlowStatusAdapter` con RLS).

### Conseguenze

- Il PnL della riga comprende il non realizzato all'ultimo ciclo, come il valore del flusso di F3.4.
- Una notifica emessa tra due cicli mostra lo stato dell'ultimo ciclo concluso.
