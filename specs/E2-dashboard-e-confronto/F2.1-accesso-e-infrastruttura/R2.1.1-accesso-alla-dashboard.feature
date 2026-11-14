# language: it
@R2.1.1
Funzionalità: R2.1.1 Accesso alla dashboard
  Come utente
  Voglio entrare nella dashboard con il mio account
  Perché gestisca i miei flussi da browser senza usare l'interfaccia programmatica

  La dashboard è privata: vi entra solo chi ha il ruolo Utente, con la stessa identità dell'interfaccia
  programmatica (R0.1.1). Ogni pagina mostra solo i dati del tenant dell'utente (R0.1.3) e l'ambiente
  dell'installazione (dev o prod) è sempre visibile (R0.1.4). Al primo accesso il tenant si crea come per
  l'interfaccia programmatica (R0.1.2). Testi solo in italiano.

  Fuori ambito: la registrazione autonoma degli utenti (F5), altre lingue.

  Contesto:
    Dato che "anna" ha il ruolo Utente e il flusso "alfa"
    E che "bruno" ha il flusso "omega"
    E che "carla" non ha il ruolo Utente

  Scenario: Accesso con il ruolo Utente
    Quando "anna" apre la dashboard ed entra con il proprio account
    Allora vede la pagina iniziale con il flusso "alfa"
    E non vede il flusso "omega"

  Scenario: Accesso negato senza ruolo
    Quando "carla" apre la dashboard ed entra con il proprio account
    Allora la dashboard mostra "Accesso non consentito: manca il ruolo Utente"
    E non mostra alcun dato

  Scenario: Accesso senza autenticazione
    Quando un visitatore apre la dashboard senza entrare
    Allora viene portato alla pagina di accesso

  Scenario: Ambiente riconoscibile
    Dato che la dashboard è quella dell'installazione dev
    Quando "anna" apre una qualsiasi pagina
    Allora la pagina mostra l'indicazione "dev"

  Scenario: Sessione scaduta
    Dato che l'accesso di "anna" è scaduto
    Quando "anna" apre la pagina del flusso "alfa"
    Allora viene portata alla pagina di accesso
    E dopo l'accesso torna alla pagina del flusso "alfa"
