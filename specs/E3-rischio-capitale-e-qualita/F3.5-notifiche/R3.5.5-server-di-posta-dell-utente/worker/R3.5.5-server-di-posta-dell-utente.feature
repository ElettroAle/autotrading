# language: it
@R3.5.5
Funzionalità: R3.5.5 Server di posta dell'utente
  Come utente
  Voglio indicare dalla dashboard il server di posta da cui partono le mie email
  Perché il canale email funzioni senza configurare nulla nell'installazione

  Ogni utente indica nella scheda Canali della pagina Notifiche il proprio server di posta (SMTP): server, porta,
  sicurezza (STARTTLS o TLS), utente, password e mittente (se vuoto, l'utente). Ce n'è uno per tenant; si può
  modificare e togliere. La password non torna mai dall'API né dalla dashboard: si vede solo che è salvata, e una
  modifica senza password conserva quella salvata. La password si conserva cifrata e la legge solo il worker.
  Senza server di posta il canale email non è disponibile: la scelta dei canali avvisa che manca il server.
  L'email di prova parte dal server dell'utente e, se il server rifiuta, l'utente vede subito il motivo.
  Le notifiche email partono dal server del tenant della notifica, mai da quello di un altro tenant.
  La pagina Notifiche ha due schede: Preferenze (predefinita, la scelta dei canali) e Canali (Telegram ed Email); si
  apre su Canali quando nessun canale è collegato.

  Contesto:
    Dato che "anna" ha indicato l'indirizzo "anna@example.com" per le notifiche

  Scenario: Le notifiche email partono dal server del tenant della notifica
    Dato che "anna" ha salvato il server di posta "smtp.example.com"
    E che "bruno" ha indicato l'indirizzo "bruno@example.com" per le notifiche
    E che "bruno" ha salvato il server di posta "smtp.bruno.example"
    Quando un ciclo di un flusso di "bruno" fallisce con il canale email scelto
    Allora "bruno@example.com" riceve la notifica dal server "smtp.bruno.example"
    E nessuna email parte dal server "smtp.example.com"
