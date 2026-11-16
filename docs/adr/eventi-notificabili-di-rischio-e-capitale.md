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

## Opzioni considerate

1. Un tipo di evento enumerato nel domain (`NotificationEvent`, con tutti i tipi di R1.8.2 e R3.5.1, ciascuno col
   nome mostrato all'utente, per esempio «pausa automatica di un flusso», e l'indicazione di evento del conto o del
   flusso) portato da ogni `Notification`; nuove factory (`position_closed` con il motivo `stop loss`/`take profit`,
   `position_liquidated`, `opening_reduced`, `opening_blocked`, `openings_suspended`, `reconciliation_alarm`,
   `withdrawal_done`, `emergency_close_done`) con i testi degli scenari; nuovi `Notify<Evento>UseCase` chiamati dai
   casi d'uso che producono l'evento. La chiusura eseguita dall'exchange passa per la stessa notifica della chiusura
   (ADR 0070) con il motivo, così non esiste una seconda notifica.
2. Una notifica generica con testo libero: scartata, R3.5.3 ha bisogno del tipo per scegliere il canale.

## Esito della decisione

Opzione 1. Il tipo di evento porta anche il flusso (per le eccezioni di R3.5.3), o nessun flusso per gli eventi del
conto. Si sviluppa dopo l'integrazione dei requisiti che generano gli eventi.

Verifica: prova (scenari di R3.5.1; unit test delle factory e dei casi d'uso).

### Conseguenze

- Ogni evento futuro aggiunge un tipo all'enumerazione e una factory; la scelta dei canali lo vede da sola.
