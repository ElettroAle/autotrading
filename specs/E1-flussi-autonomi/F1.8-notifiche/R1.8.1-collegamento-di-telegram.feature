# language: it
@R1.8.1
Funzionalità: R1.8.1 Collegamento di Telegram
  Come utente
  Voglio collegare la mia chat Telegram al mio tenant
  Perché le notifiche dei miei flussi arrivino a me e a nessun altro

  La piattaforma ha un solo bot Telegram. L'utente chiede un codice di collegamento, valido 15 minuti e usabile
  una sola volta, e lo invia al bot dalla propria chat: da quel momento la chat riceve le notifiche del suo
  tenant. Un tenant ha al massimo una chat collegata; un nuovo collegamento sostituisce il precedente.
  L'utente può scollegare la chat. Senza chat collegata le notifiche non si inviano e i flussi operano
  normalmente.
  Un messaggio al bot con un codice scaduto, già usato o inesistente non collega nulla e riceve una risposta
  che non rivela se il codice è esistito.

  Fuori ambito: email, scelta dei canali per evento, più chat per tenant.

  Contesto:
    Dato che "anna" non ha una chat Telegram collegata

  Scenario: Collegamento con un codice valido
    Dato che "anna" ha chiesto un codice di collegamento alle 10:00
    Quando la chat "chat-anna" invia il codice al bot alle 10:10
    Allora la chat "chat-anna" è collegata al tenant di "anna"
    E il bot risponde alla chat "chat-anna" che il collegamento è riuscito

  Schema dello scenario: Codice non valido
    Dato che "anna" ha chiesto un codice di collegamento alle 10:00
    E che <condizione>
    Quando la chat "chat-x" invia il codice al bot
    Allora la chat "chat-x" non è collegata ad alcun tenant
    E il bot risponde alla chat "chat-x" "codice non valido"

    Esempi:
      | condizione                                       |
      | sono le 10:16                                    |
      | il codice è già stato usato dalla chat "chat-anna" |

  Scenario: Nuovo collegamento sostituisce il precedente
    Dato che la chat "chat-anna" è collegata al tenant di "anna"
    Quando "anna" collega la chat "chat-anna-2"
    Allora la chat "chat-anna-2" è collegata al tenant di "anna"
    E la chat "chat-anna" non riceve più le notifiche di "anna"

  Scenario: Scollegamento
    Dato che la chat "chat-anna" è collegata al tenant di "anna"
    Quando "anna" scollega la chat Telegram
    Allora la chat "chat-anna" non riceve più le notifiche di "anna"
