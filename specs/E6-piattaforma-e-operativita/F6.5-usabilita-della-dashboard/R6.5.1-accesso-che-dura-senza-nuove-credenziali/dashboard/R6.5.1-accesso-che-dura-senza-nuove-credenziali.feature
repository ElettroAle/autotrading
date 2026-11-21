# language: it
@R6.5.1
Funzionalità: R6.5.1 Accesso che dura senza nuove credenziali
  Come utente
  Voglio riaprire la dashboard senza reinserire le credenziali a ogni sessione del browser
  Perché l'accesso chiesto troppo spesso rende scomodo controllare i flussi

  Entra limita il refresh token di una SPA a 24 ore fisse: i 30 giorni non si ottengono sul token, si ottengono
  evitando le credenziali. I token MSAL stanno in localStorage, così l'accesso sopravvive alla chiusura della scheda
  e del browser. Quando il refresh token scade, la dashboard rinnova con acquireTokenRedirect sulla sessione Entra
  ancora valida: un rimbalzo senza credenziali. Si chiedono le credenziali solo quando la sessione Entra è finita.
  Poiché i token in localStorage sono leggibili da uno script nella pagina, il server della dashboard serve una
  Content Security Policy rigida (script e stili solo dalla propria origine, connessioni solo verso l'API e Entra,
  nessun inline, nessun frame). «Esci» cancella ogni token e ogni dato di sessione dal browser e chiude la sessione
  Entra.
  Sostituisce l'ADR 0118 (token in sessionStorage, nessun rinnovo senza interazione): la nuova ADR si scrive alla
  presa in carico, con l'approvazione del proprietario.

  Contesto:
    Dato che "anna" ha fatto l'accesso alla dashboard e la sua sessione Entra è valida

  Scenario: Riapertura dopo la chiusura del browser
    Dato che "anna" chiude il browser
    Quando riapre la dashboard il giorno dopo
    Allora vede i suoi flussi senza inserire le credenziali

  Scenario: Rinnovo alla scadenza del refresh token
    Dato che il refresh token di "anna" è scaduto
    Quando la dashboard chiama l'API
    Allora la dashboard rinnova i token con un redirect a Entra senza chiedere le credenziali
    E torna alla pagina in cui "anna" si trovava

  Scenario: Sessione Entra finita
    Dato che la sessione Entra di "anna" è finita
    Quando "anna" apre la dashboard
    Allora Entra le chiede le credenziali

  Scenario: Uscita
    Quando "anna" sceglie «Esci»
    Allora nel browser non resta alcun token né dato di sessione
    E riaprendo la dashboard le vengono chieste le credenziali

  Scenario: Content Security Policy rigida
    Quando il browser carica una pagina della dashboard
    Allora la risposta porta una Content Security Policy che ammette script e stili solo dalla propria origine
    E connessioni solo verso l'API e Entra, senza script inline né frame
