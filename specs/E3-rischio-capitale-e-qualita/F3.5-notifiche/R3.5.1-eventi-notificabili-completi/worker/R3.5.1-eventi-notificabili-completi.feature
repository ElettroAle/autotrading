# language: it
@R3.5.1
Funzionalità: R3.5.1 Eventi notificabili completi
  Come utente
  Voglio essere avvisato anche degli eventi di rischio e di capitale dei miei flussi
  Perché so subito quando una protezione scatta o quando la piattaforma blocca qualcosa

  Agli eventi già notificati (R1.8.2) si aggiungono (RF-24.03):
  - stop loss attivato e take profit attivato (R3.1.2): è la notifica della chiusura, con il motivo;
  - liquidazione di una posizione del flusso;
  - decisione ridotta dal rischio e decisione bloccata dal rischio (R1.5.1-R1.5.4, R3.1.4, R3.2.1);
  - perdita massima raggiunta (R3.2.2);
  - allarme di riconciliazione (R3.3.1);
  - incasso eseguito (R3.4.1);
  - chiusura di emergenza eseguita (R3.2.3).
  Ogni evento si notifica una volta. La chiusura per stop loss, take profit o liquidazione produce una sola
  notifica, non una per la chiusura e una per il motivo.
  L'insieme di questi tipi di evento e di quelli di R1.8.2 è l'elenco su cui l'utente sceglie i canali (R3.5.3).
  Valgono le regole di R1.8.2: nessuna credenziale, solo al tenant dell'evento, un invio fallito non ferma il ciclo.
  Fuori ambito: la fine di un replay, che arriva con il replay (E4); i riepiloghi periodici (R5.4.4).

  Contesto:
    Dato che "anna" ha la chat "chat-anna" collegata, il conto "test-1" e il flusso "alfa"
    E che "bruno" ha la chat "chat-bruno" collegata
  Schema dello scenario: Eventi notificati
    Quando <evento>
    Allora la chat "chat-anna" riceve una notifica "<titolo>" con le righe "<righe>"
    E la chat "chat-bruno" non riceve la notifica
    Esempi:
      | evento                                                                                     | titolo                               | righe                                                                |
      | l'exchange esegue lo stop loss di "alfa" su "BTC" con PnL -5,10 USDC                       | 🛑 alfa: chiusa per stop loss         | Asset: BTC; PnL: -5,10 USDC                                          |
      | l'exchange esegue il take profit di "alfa" su "BTC" con PnL 4,90 USDC                      | 🎯 alfa: chiusa per take profit       | Asset: BTC; PnL: 4,90 USDC                                           |
      | l'exchange liquida la posizione di "alfa" su "BTC" con PnL -48,25 USDC                     | 🔻 alfa: posizione liquidata          | Asset: BTC; PnL: -48,25 USDC                                         |
      | il rischio riduce l'apertura di "alfa" su "BTC" da 150 a 100 USDC di margine               | ⚠️ alfa: apertura ridotta            | Asset: BTC; Margine richiesto: 150 USDC; Margine approvato: 100 USDC |
      | il rischio blocca l'apertura di "alfa" su "BTC" per confidenza 40 sotto la minima 60       | ⚠️ alfa: apertura non eseguita       | Asset: BTC; Motivo: confidenza 40 sotto la minima 60                 |
      | le aperture di "alfa" si sospendono per perdita giornaliera 6% oltre il 5%                 | ⏸️ alfa: aperture sospese            | Motivo: perdita giornaliera 6% oltre il 5%                           |
      | sul conto "test-1" si apre un allarme di riconciliazione con saldo 980 invece di 1000 USDC | 🚨 test-1: allarme di riconciliazione | Saldo letto: 980 USDC; Saldo atteso: 1000 USDC                       |
      | "anna" incassa 118 USDC dal flusso "alfa"                                                  | ✅ alfa: incasso eseguito             | Importo: 118 USDC                                                    |
      | "anna" lancia la chiusura di emergenza del flusso "alfa" con 1 posizione chiusa            | 🚨 chiusura di emergenza: eseguita    | Posizioni chiuse: 1; Flussi in pausa: alfa                           |
  Schema dello scenario: Una sola notifica per la chiusura
    Dato che "alfa" ha una posizione aperta su "BTC"
    Quando la posizione di "alfa" su "BTC" si chiude per <motivo>
    Allora la chat "chat-anna" riceve una sola notifica per quella chiusura
    Esempi:
      | motivo       |
      | stop loss    |
      | take profit  |
      | liquidazione |
  Scenario: Invio fallito non ferma il ciclo
    Dato che l'invio delle notifiche alla chat "chat-anna" fallisce
    Quando il rischio riduce un'apertura di "alfa" su "BTC"
    Allora il ciclo di "alfa" si conclude ed esegue l'apertura ridotta
  Schema dello scenario: Le notifiche dei nuovi eventi non contengono credenziali
    Quando <evento>
    Allora la chat "chat-anna" riceve una notifica "<titolo>" con le righe "<righe>"
    E nessuna notifica della chat "chat-anna" contiene le credenziali del conto del flusso "alfa"
    Esempi:
      | evento                                                                                     | titolo                               | righe                                          |
      | l'exchange esegue lo stop loss di "alfa" su "BTC" con PnL -5,10 USDC                       | 🛑 alfa: chiusa per stop loss         | Asset: BTC; PnL: -5,10 USDC                    |
      | l'exchange liquida la posizione di "alfa" su "BTC" con PnL -48,25 USDC                     | 🔻 alfa: posizione liquidata          | Asset: BTC; PnL: -48,25 USDC                   |
      | sul conto "test-1" si apre un allarme di riconciliazione con saldo 980 invece di 1000 USDC | 🚨 test-1: allarme di riconciliazione | Saldo letto: 980 USDC; Saldo atteso: 1000 USDC |
      | "anna" lancia la chiusura di emergenza del flusso "alfa" con 1 posizione chiusa            | 🚨 chiusura di emergenza: eseguita    | Posizioni chiuse: 1; Flussi in pausa: alfa     |
