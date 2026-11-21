# language: it
@R3.5.2
Funzionalità: R3.5.2 Notifiche via email
  Come utente
  Voglio ricevere le notifiche anche per email
  Perché ho un secondo canale quando non guardo Telegram

  L'utente indica un indirizzo email per le notifiche, dall'interfaccia programmatica e dalle Impostazioni della
  dashboard. L'indirizzo vale subito, senza verifica; ce n'è uno per tenant; si può cambiare e togliere. Un indirizzo
  che non ha la forma di un indirizzo email viene rifiutato.
  L'utente può chiedere un'email di prova all'indirizzo indicato.
  Una notifica destinata all'email (R3.5.3) ha per oggetto il flusso o il conto e l'evento, e per testo lo stesso
  testo della notifica su Telegram.
  Un invio che fallisce si registra, si ritenta come le altre notifiche e non fa fallire il ciclo.
  Le email partono dal server di posta del tenant (R3.5.5). Se il tenant non ha un server di posta, il canale email non
  è disponibile: l'indirizzo si può indicare, la dashboard avvisa che le email non partono, e la prova risponde con lo
  stesso avviso.
  Un'email non contiene mai credenziali.

  Contesto:
    Dato che "anna" ha un server di posta configurato
    E che "anna" ha il flusso "alfa" con il canale email scelto per l'evento "pausa automatica di un flusso"
  Scenario: Indirizzo indicato
    Quando "anna" indica l'indirizzo "anna@example.com" per le notifiche
    Allora le Impostazioni di "anna" mostrano l'indirizzo "anna@example.com"
  Schema dello scenario: Indirizzo malformato
    Quando "anna" indica l'indirizzo "<indirizzo>" per le notifiche
    Allora la richiesta viene rifiutata con "indirizzo email non valido"
    Esempi:
      | indirizzo    |
      | anna         |
      | anna@        |
      | @example.com |
  Scenario: Email di prova
    Dato che "anna" ha indicato l'indirizzo "anna@example.com"
    Quando "anna" chiede un'email di prova
    Allora "anna@example.com" riceve un'email con oggetto "🔔 AutoTrading: prova delle notifiche"
  Scenario: Notifica ricevuta per email
    Dato che "anna" ha indicato l'indirizzo "anna@example.com"
    Quando il flusso "alfa" va in pausa per "credito esaurito"
    Allora "anna@example.com" riceve un'email con oggetto "⏸️ alfa: in pausa" e le righe "Motivo: credito esaurito"
  Scenario: Indirizzo cambiato
    Dato che "anna" ha indicato l'indirizzo "anna@example.com"
    Quando "anna" indica l'indirizzo "anna2@example.com" e il flusso "alfa" va in pausa
    Allora "anna2@example.com" riceve l'email
    E "anna@example.com" non riceve l'email
  Scenario: Indirizzo tolto
    Dato che "anna" ha indicato l'indirizzo "anna@example.com"
    Quando "anna" toglie l'indirizzo e il flusso "alfa" va in pausa
    Allora "anna@example.com" non riceve l'email
  Scenario: Invio fallito non ferma il ciclo
    Dato che "anna" ha indicato l'indirizzo "anna@example.com" e il server di posta rifiuta gli invii
    Quando un ciclo di "alfa" produce una notifica destinata all'email
    Allora il ciclo di "alfa" si conclude
    E l'invio fallito è registrato
  Scenario: Tenant senza server di posta
    Dato che "anna" non ha un server di posta configurato
    Quando "anna" apre le Impostazioni delle notifiche
    Allora la pagina avvisa "le email non partono: server di posta non configurato"
  Scenario: Prova senza server di posta
    Dato che "anna" non ha un server di posta configurato
    Quando "anna" chiede un'email di prova
    Allora la richiesta viene rifiutata con "server di posta non configurato"
  Scenario: Indirizzi isolati per tenant
    Dato che "bruno" ha indicato l'indirizzo "bruno@example.com"
    Quando il flusso "alfa" di "anna" va in pausa
    Allora "bruno@example.com" non riceve l'email
  Scenario: Un invio fallito si ritenta
    Dato che "anna" ha indicato l'indirizzo "anna@example.com" e il server di posta rifiuta gli invii
    E che un ciclo di "alfa" ha prodotto una notifica destinata all'email
    Quando il server di posta torna ad accettare gli invii e arriva il nuovo tentativo
    Allora "anna@example.com" riceve un'email con oggetto "🟢 alfa: posizione aperta"
  Scenario: Un'email non contiene mai credenziali
    Dato che "anna" ha indicato l'indirizzo "anna@example.com"
    Quando il flusso "alfa" va in pausa per "credito esaurito"
    Allora "anna@example.com" riceve l'email
    E nessuna email di "anna@example.com" contiene le credenziali del conto di "alfa" né la password del server di posta
