# language: it
@R6.2.1
Funzionalità: R6.2.1 Campanello delle notifiche
  Come utente
  Voglio vedere le notifiche anche nella dashboard, da un campanello
  Perché non perdo un avviso se non guardo Telegram

  In alto a destra, accanto al nome dell'utente, un campanello mostra il numero di notifiche non lette e, aperto,
  l'elenco delle notifiche dalla più recente: titolo, testo, data e ora, e il collegamento alla pagina interessata
  (flusso, conto, chiave). Ogni notifica che la piattaforma invia su Telegram compare anche nel campanello, anche
  se Telegram non è collegato o l'invio fallisce. Le notifiche si segnano come lette una per una o tutte insieme e
  si conservano 90 giorni. Il numero si aggiorna con la rilettura della dashboard (R2.1.2). Le notifiche
  appartengono al tenant.

  Contesto:
    Dato che "anna" è nella dashboard

  Scenario: Notifiche non lette nel campanello
    Dato che "anna" ha 3 notifiche non lette
    Quando "anna" guarda il campanello accanto al suo nome
    Allora il campanello mostra 3

  Scenario: Elenco e collegamento
    Dato che "anna" ha la notifica "Flusso alfa in pausa"
    Quando "anna" apre il campanello e sceglie la notifica
    Allora la dashboard apre la pagina del flusso "alfa" e la notifica è letta

  Scenario: Tutte lette
    Dato che "anna" ha 3 notifiche non lette
    Quando "anna" le segna tutte come lette
    Allora il campanello non mostra alcun numero

  Scenario: Notifiche isolate per tenant
    Dato che "bruno" ha una notifica
    Quando "anna" apre il campanello
    Allora la notifica di "bruno" non compare
