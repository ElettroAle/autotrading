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
  Il codice si può inviare da solo o dopo il comando di avvio del bot, come fa il link t.me/<bot>?start=<codice>
  che la piattaforma restituisce insieme al codice quando il bot è attivo: un tocco apre la chat e collega.
  Dalla chat collegata il comando /prova fa arrivare una notifica di prova per la stessa strada delle notifiche
  dei flussi, così l'utente vede che la consegna funziona senza attendere un evento di un flusso.
  Un messaggio senza codice, come il solo comando di avvio o un altro comando, riceve le istruzioni per il
  collegamento.

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

  Scenario: Il codice arriva con il link del bot
    Dato che il bot della piattaforma si chiama "autotrading_bot"
    Quando "anna" chiede un codice di collegamento
    Allora insieme al codice arriva il link "https://t.me/autotrading_bot?start=" seguito dal codice

  Scenario: Senza bot attivo il codice arriva senza link
    Dato che il bot della piattaforma non è attivo
    Quando "anna" chiede un codice di collegamento
    Allora insieme al codice non arriva alcun link

  Scenario: Collegamento dal link del bot
    Dato che "anna" ha chiesto un codice di collegamento alle 10:00
    Quando la chat "chat-anna" invia il comando di avvio seguito dal codice alle 10:05
    Allora la chat "chat-anna" è collegata al tenant di "anna"
    E il bot risponde alla chat "chat-anna" che il collegamento è riuscito

  Schema dello scenario: Messaggio senza codice
    Quando la chat "chat-x" invia "<messaggio>" al bot
    Allora la chat "chat-x" non è collegata ad alcun tenant
    E il bot risponde alla chat "chat-x" con le istruzioni per il collegamento

    Esempi:
      | messaggio |
      | /start    |
      | /help     |

  Scenario: Nuovo collegamento sostituisce il precedente
    Dato che la chat "chat-anna" è collegata al tenant di "anna"
    Quando "anna" collega la chat "chat-anna-2"
    Allora la chat "chat-anna-2" è collegata al tenant di "anna"
    E la chat "chat-anna" non riceve più le notifiche di "anna"

  Scenario: Scollegamento
    Dato che la chat "chat-anna" è collegata al tenant di "anna"
    Quando "anna" scollega la chat Telegram
    Allora la chat "chat-anna" non riceve più le notifiche di "anna"

  Scenario: Prova dalla chat collegata
    Dato che la chat "chat-anna" è collegata al tenant di "anna"
    Quando la chat "chat-anna" invia "/prova" al bot
    Allora il bot invia alla chat "chat-anna" "notifica di prova: le notifiche dei tuoi flussi arrivano qui"

  Scenario: Prova da una chat non collegata
    Quando la chat "chat-x" invia "/prova" al bot
    Allora il bot risponde alla chat "chat-x" con le istruzioni per il collegamento
