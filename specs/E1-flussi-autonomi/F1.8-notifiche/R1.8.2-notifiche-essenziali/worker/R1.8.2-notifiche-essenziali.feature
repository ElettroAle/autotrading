# language: it
@R1.8.2
Funzionalità: R1.8.2 Notifiche essenziali su Telegram
  Come utente
  Voglio ricevere su Telegram gli eventi importanti dei miei flussi
  Perché mi accorga di ciò che succede senza consultare la piattaforma

  Si notificano: apertura e chiusura di una posizione, ciclo fallito, ordine rifiutato dall'exchange, pausa
  automatica di un flusso, posizione o esecuzione non attribuibile su un conto. Una variazione del saldo entro la soglia
  del conto non si notifica: si registra e si consulta nel conto (R1.6.2, R3.3.1).
  Ogni notifica nomina il flusso (o il conto) e l'evento, con i valori essenziali uno per riga (R3.5.4): per
  un'apertura asset, direzione, leva e valore; per una chiusura asset e PnL; per un errore il messaggio originale.
  Una notifica non contiene mai credenziali. Le notifiche vanno solo alla chat collegata al tenant (R1.8.1).
  Un invio che fallisce si registra e non fa fallire il ciclo.
  Ogni chiusura di una posizione di un flusso si notifica una volta, qualunque ne sia il motivo (decisione
  dell'agente, stop del flusso, rimozione del conto, comando manuale, chiusura fuori dalla piattaforma), con lo
  stesso PnL che entra nello storico delle posizioni chiuse: quello che l'exchange riporta.

  Fuori ambito: la scelta degli eventi e dei canali, l'email, i riepiloghi periodici.

  Contesto:
    Dato che "anna" ha la chat "chat-anna" collegata e il flusso "alfa"
    E che "bruno" ha la chat "chat-bruno" collegata

  Schema dello scenario: Eventi notificati
    Quando <evento>
    Allora la chat "chat-anna" riceve una notifica "<titolo>" con le righe "<righe>"
    E la chat "chat-bruno" non riceve la notifica

    Esempi:
      | evento                                                                | titolo                     | righe                                                  |
      | il flusso "alfa" apre long su "BTC" con leva 3 e valore 150 USDC      | 🟢 alfa: posizione aperta   | Asset: BTC; Direzione: long; Leva: 3; Valore: 150 USDC |
      | il flusso "alfa" chiude la posizione su "BTC" con PnL 4,20 USDC       | ✅ alfa: posizione chiusa   | Asset: BTC; PnL: 4,20 USDC                             |
      | un ciclo del flusso "alfa" fallisce con il messaggio "timeout"        | ⚠️ alfa: ciclo fallito     | Errore: timeout                                        |
      | l'exchange rifiuta un ordine del flusso "alfa" con "Order rejected"   | ⚠️ alfa: ordine rifiutato  | Errore: Order rejected                                 |
      | il flusso "alfa" va in pausa per "credito esaurito presso openrouter" | ⏸️ alfa: in pausa          | Motivo: credito esaurito presso openrouter             |
      | sul conto di "alfa" compare una posizione non attribuibile su "SOL"   | posizione non attribuibile | Asset: SOL                                             |

  Schema dello scenario: Ogni chiusura notificata una volta
    Dato che il flusso "alfa" ha una posizione aperta su "BTC"
    Quando la posizione su "BTC" del flusso "alfa" si chiude per <motivo> con PnL 4,20 USDC
    Allora la chat "chat-anna" riceve una sola notifica "✅ alfa: posizione chiusa" con le righe "Asset: BTC; PnL: 4,20 USDC"

    Esempi:
      | motivo                 |
      | decisione dell'agente  |
      | stop del flusso        |
      | rimozione del conto    |
      | comando manuale        |

  Scenario: Notifica e storico con lo stesso PnL
    Dato che il flusso "alfa" ha una posizione aperta su "BTC"
    Quando la posizione su "BTC" del flusso "alfa" si chiude per decisione dell'agente con PnL 4,20 USDC
    Allora lo storico del flusso "alfa" contiene la posizione su "BTC" con PnL 4,20 USDC

  Scenario: Invio fallito non ferma il ciclo
    Dato che Telegram non risponde
    Quando il flusso "alfa" apre una posizione su "BTC"
    Allora il ciclo del flusso "alfa" si conclude
    E l'invio fallito della notifica è registrato

  Scenario: Senza chat collegata
    Dato che "anna" ha scollegato la chat Telegram
    Quando il flusso "alfa" apre una posizione su "BTC"
    Allora nessuna notifica viene inviata
    E il ciclo del flusso "alfa" si conclude
