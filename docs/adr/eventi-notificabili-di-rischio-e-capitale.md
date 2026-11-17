# ADR eventi-notificabili-di-rischio-e-capitale — Eventi notificabili di rischio e capitale

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.5.1 (467), Task T3.5.1.1 (491); RF-24.03
- Collegate: ADR 0092 (notifiche come passi dei casi d'uso), ADR 0070 (ogni chiusura notificata con il PnL
  dell'exchange), ADR canale-email-delle-notifiche-con-smtp

## Contesto e problema

R1.8.2 notifica aperture, chiusure, cicli falliti, ordini rifiutati, pause e movimenti non attribuibili. R3.5.1
aggiunge gli eventi di E3: chiusura per stop loss o take profit, liquidazione, decisione ridotta o bloccata dal
rischio, perdita massima, allarme di riconciliazione, incasso, chiusura di emergenza. Gli eventi nascono nei casi
d'uso di R3.1.2, R3.2.1-R3.2.3, R3.3.1 e R3.4.1, che devono essere già integrati.

## Fattori decisionali

- ADR 0092: la notifica è un passo esplicito del caso d'uso che produce l'evento, attraverso un
  `Notify<Evento>UseCase` del contesto `notifications`, mai un decorator o un ponte.
- R3.5.1: ogni evento si notifica una volta; una chiusura per stop loss, take profit o liquidazione è una sola
  notifica con il motivo.
- R3.5.3: l'elenco dei tipi di evento è quello su cui si scelgono i canali.

## Stato di main (17 novembre 2026, dopo F3.1-F3.4)

Una parte degli eventi è già notificata, ma come testo senza tipo:

- `openings_suspended` (perdita massima di R3.2.2 con `GuardFlowLossUseCase`, allarme di R3.3.1) e
  `reconciliation_alarm` esistono e sono chiamate;
- le chiusure per protezione passano da `RecordProtectionClosingUseCase` alla notifica della chiusura
  (`PositionClosedNoticePort`), ma senza il motivo nel testo;
- la liquidazione non ha un motivo proprio: è una chiusura `OUTSIDE_PLATFORM`, anche se l'esecuzione registrata dal
  registro porta già il flag `liquidation` (ADR 0076);
- riduzione e blocco dal rischio, incasso (`CashOutProfitsUseCase`) e chiusura di emergenza (`CloseInEmergencyUseCase`)
  non notificano nulla.

## Opzioni considerate

1. Un tipo di evento enumerato nel domain (`NotificationEvent`, con tutti i tipi di R1.8.2 e R3.5.1, ciascuno col
   nome mostrato all'utente, per esempio «pausa automatica di un flusso», e l'indicazione di evento del conto o del
   flusso) portato da ogni `Notification`. Nel dettaglio:
   - le factory esistenti (`openings_suspended`, `reconciliation_alarm` e le altre di R1.8.2) prendono il loro tipo,
     senza cambiare chi le chiama;
   - `position_closed` riceve il motivo della chiusura: la porta `PositionClosedNoticePort.execute` riceve anche il
     motivo (`CloseReason` come testo), e il testo diventa «chiusa BTC per stop loss» per stop loss, take profit e
     liquidazione. Così la chiusura eseguita dall'exchange resta una sola notifica (ADR 0070);
   - liquidazione: `CloseReason.LIQUIDATION` («liquidazione»), scelto da `RecordOutsideClosingUseCase` quando
     l'esecuzione di chiusura registrata porta il flag `liquidation`, altrimenti resta `OUTSIDE_PLATFORM`; la factory
     `position_liquidated` dà «liquidata BTC»;
   - nuove factory e nuovi `Notify<Evento>UseCase`: `opening_reduced` e `opening_blocked`, chiamate da
     `ReviewCycleRiskUseCase` per ogni apertura ridotta o bloccata; `cash_out_done`, chiamata da
     `CashOutProfitsUseCase`; `emergency_closing_done`, chiamata da `CloseInEmergencyUseCase` una volta per chiusura
     di emergenza, con il numero di posizioni chiuse e i flussi messi in pausa;
   - le chiusure delle singole posizioni di un'emergenza (`CloseReason.EMERGENCY`) non si notificano una per una:
     l'evento è la chiusura di emergenza, e la sua notifica le riassume.

   Ogni nuovo `Notify<Evento>UseCase` realizza una porta `*NoticePort` dichiarata in `application/flows/ports.py` dal
   contesto che produce l'evento (ADR 0092).
2. Una notifica generica con testo libero: scartata, R3.5.3 ha bisogno del tipo per scegliere il canale.

## Esito della decisione

Opzione 1. Il tipo di evento porta anche il flusso (per le eccezioni di R3.5.3), o nessun flusso per gli eventi del
conto. I testi degli scenari sono quelli di R3.5.1; R3.5.4 li porta poi nel formato con icona, titolo e righe (ADR
notifica-strutturata-con-icona-titolo-e-valori).

Verifica: prova (scenari di R3.5.1; unit test delle factory e dei casi d'uso).

### Conseguenze

- Ogni evento futuro aggiunge un tipo all'enumerazione e una factory; la scelta dei canali lo vede da sola.
