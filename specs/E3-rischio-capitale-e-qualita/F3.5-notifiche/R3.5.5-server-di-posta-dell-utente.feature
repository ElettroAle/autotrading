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

  Scenario: Server di posta salvato senza mostrare la password
    Quando "anna" salva il server di posta "smtp.example.com" porta 587 con STARTTLS, utente "anna@example.com" e una password
    Allora i Canali di "anna" mostrano il server "smtp.example.com:587 · STARTTLS · anna@example.com · password salvata"
    E la password non compare nella risposta

  Scenario: Senza server di posta il canale email non è disponibile
    Allora la scelta dei canali di "anna" avvisa accanto all'email con "server di posta non configurato"

  Scenario: Email di prova dal server dell'utente
    Dato che "anna" ha salvato il server di posta "smtp.example.com"
    Quando "anna" invia l'email di prova
    Allora "anna@example.com" riceve l'email di prova da "smtp.example.com"

  Scenario: Credenziali rifiutate dal server di posta
    Dato che "anna" ha salvato il server di posta "smtp.example.com"
    E che il server di posta rifiuta l'accesso
    Quando "anna" invia l'email di prova
    Allora la richiesta viene rifiutata con "il server di posta ha rifiutato l'accesso: controlla utente e password"

  Scenario: Modifica senza riscrivere la password
    Dato che "anna" ha salvato il server di posta "smtp.example.com"
    Quando "anna" cambia la porta del server di posta in 465 con TLS senza indicare la password
    Allora l'email di prova parte da "smtp.example.com:465" con la password salvata

  Scenario: Server di posta tolto
    Dato che "anna" ha salvato il server di posta "smtp.example.com"
    Quando "anna" toglie il server di posta
    Allora la scelta dei canali di "anna" avvisa accanto all'email con "server di posta non configurato"

  Scenario: Server di posta isolato per tenant
    Dato che "anna" ha salvato il server di posta "smtp.example.com"
    E che "bruno" ha indicato l'indirizzo "bruno@example.com" per le notifiche
    Allora i Canali di "bruno" non mostrano alcun server di posta
    E la scelta dei canali di "bruno" avvisa accanto all'email con "server di posta non configurato"
