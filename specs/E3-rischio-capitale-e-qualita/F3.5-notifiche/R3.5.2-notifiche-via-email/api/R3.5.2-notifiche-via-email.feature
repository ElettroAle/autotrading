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
  Scenario: Tenant senza server di posta
    Dato che "anna" non ha un server di posta configurato
    Quando "anna" apre le Impostazioni delle notifiche
    Allora la pagina avvisa "le email non partono: server di posta non configurato"
  Scenario: Prova senza server di posta
    Dato che "anna" non ha un server di posta configurato
    Quando "anna" chiede un'email di prova
    Allora la richiesta viene rifiutata con "server di posta non configurato"
