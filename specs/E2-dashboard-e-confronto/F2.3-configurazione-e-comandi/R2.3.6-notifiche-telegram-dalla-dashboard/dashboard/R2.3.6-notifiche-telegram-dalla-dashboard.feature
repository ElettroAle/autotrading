# language: it
@R2.3.6
Funzionalità: R2.3.6 Notifiche Telegram dalla dashboard
  Come utente
  Voglio collegare Telegram e provare le notifiche dalla dashboard
  Perché riceva le notifiche dei miei flussi senza usare l'interfaccia programmatica

  Dalla dashboard l'utente genera il codice di collegamento con il link del bot (R1.8.1), vede la chat
  collegata, la scollega e invia una notifica di prova alla chat collegata, con le regole di R1.8.1.

  Fuori ambito: la scelta dei canali e le notifiche email (F3).

  Contesto:
    Dato che "anna" è nella pagina delle notifiche

  Scenario: Codice di collegamento
    Quando "anna" chiede il codice di collegamento
    Allora la dashboard mostra il codice con la sua scadenza e il link del bot

  Scenario: Chat collegata
    Dato che "anna" ha collegato la chat "anna_tg"
    Quando "anna" apre la pagina delle notifiche
    Allora la dashboard mostra la chat "anna_tg" come collegata

  Scenario: Notifica di prova
    Dato che "anna" ha collegato la chat "anna_tg"
    Quando "anna" invia una notifica di prova
    Allora la chat "anna_tg" riceve la notifica di prova
    E la dashboard conferma l'invio

  Scenario: Prova senza chat collegata
    Dato che "anna" non ha chat collegate
    Quando "anna" apre la pagina delle notifiche
    Allora la dashboard mostra "Nessuna chat collegata"
    E il comando di prova non è disponibile

  Scenario: Scollegamento
    Dato che "anna" ha collegato la chat "anna_tg"
    Quando "anna" scollega la chat e conferma
    Allora la dashboard mostra "Nessuna chat collegata"
