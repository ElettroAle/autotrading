# language: it
@R3.5.3
Funzionalità: R3.5.3 Scelta dei canali delle notifiche
  Come utente
  Voglio scegliere su quale canale ricevere ogni tipo di evento
  Perché ricevo gli avvisi importanti dove li vedo e non sono sommerso dagli altri

  Nelle Impostazioni delle notifiche, e dall'interfaccia programmatica, l'utente sceglie per ogni tipo di evento
  (R1.8.2, R3.5.1) i canali, attivando o disattivando ciascuno: "Telegram", "email", tutti e due o "nessuno"
  (RF-24.04). La scelta vale per tutti i suoi flussi.
  Finché l'utente non sceglie, valgono i predefiniti: "nessuno" per decisione ridotta dal rischio e decisione bloccata
  dal rischio, "Telegram" per tutti gli altri tipi.
  Ogni flusso può avere eccezioni: per un tipo di evento, canali diversi da quelli generali. Senza eccezione il
  flusso segue la scelta generale. Un'eccezione si può togliere. Gli eventi del conto (posizione o movimento non
  attribuibile, allarme di riconciliazione) seguono solo la scelta generale.
  Se un canale scelto non è collegato (nessuna chat Telegram, nessun indirizzo email), la notifica non parte su quel
  canale e le Impostazioni lo avvisano accanto al tipo di evento.
  La scelta dei canali non riguarda il campanello della dashboard, che riceve ogni notifica (R6.2.1).

  Contesto:
    Dato che "anna" ha la chat "chat-anna" collegata e l'indirizzo "anna@example.com" per le notifiche
    E che "anna" ha i flussi "alfa" e "beta"
  Schema dello scenario: Canali predefiniti
    Quando "anna" apre le Impostazioni delle notifiche senza aver mai scelto
    Allora il tipo di evento "<evento>" ha il canale "<canale>"
    Esempi:
      | evento                         | canale   |
      | apertura di una posizione      | Telegram |
      | chiusura di una posizione      | Telegram |
      | ciclo fallito                  | Telegram |
      | pausa automatica di un flusso  | Telegram |
      | allarme di riconciliazione     | Telegram |
      | decisione ridotta dal rischio  | nessuno  |
      | decisione bloccata dal rischio | nessuno  |
  Schema dello scenario: Canale scelto per un tipo di evento
    Dato che "anna" sceglie il canale "<canale>" per "ciclo fallito"
    Quando un ciclo di "alfa" fallisce
    Allora la chat "chat-anna" <telegram> la notifica
    E "anna@example.com" <email> la notifica
    Esempi:
      | canale            | telegram   | email      |
      | Telegram          | riceve     | non riceve |
      | email             | non riceve | riceve     |
      | Telegram ed email | riceve     | riceve     |
      | nessuno           | non riceve | non riceve |
  Scenario: La scelta generale vale per tutti i flussi
    Dato che "anna" sceglie il canale "email" per "ciclo fallito"
    Quando un ciclo di "beta" fallisce
    Allora "anna@example.com" riceve la notifica
    E la chat "chat-anna" non riceve la notifica
  Scenario: Eccezione di un flusso
    Dato che "anna" sceglie il canale "nessuno" per "apertura di una posizione"
    E che "anna" imposta per il flusso "alfa" l'eccezione "apertura di una posizione" sul canale "Telegram"
    Quando "alfa" e "beta" aprono una posizione ciascuno
    Allora la chat "chat-anna" riceve la notifica dell'apertura di "alfa"
    E la chat "chat-anna" non riceve la notifica dell'apertura di "beta"
  Scenario: Eccezione tolta
    Dato che "anna" sceglie il canale "nessuno" per "apertura di una posizione"
    E che "anna" ha tolto l'eccezione "apertura di una posizione" del flusso "alfa"
    Quando "alfa" apre una posizione
    Allora la chat "chat-anna" non riceve la notifica
  Scenario: Gli eventi del conto non hanno eccezioni per flusso
    Quando "anna" imposta per il flusso "alfa" un'eccezione per "allarme di riconciliazione"
    Allora la richiesta viene rifiutata con "allarme di riconciliazione è un evento del conto: segue la scelta generale"
  Schema dello scenario: Canale scelto ma non collegato
    Dato che "anna" non ha <collegamento>
    Quando "anna" sceglie il canale "<canale>" per "ciclo fallito"
    Allora le Impostazioni avvisano accanto a "ciclo fallito" con "<avviso>"
    Esempi:
      | collegamento                        | canale   | avviso                 |
      | una chat Telegram collegata         | Telegram | Telegram non collegato |
      | un indirizzo email per le notifiche | email    | email non indicata     |
  Scenario: Scelte isolate per tenant
    Dato che "bruno" sceglie il canale "nessuno" per "ciclo fallito"
    Quando un ciclo di "alfa" di "anna" fallisce
    Allora la chat "chat-anna" riceve la notifica
