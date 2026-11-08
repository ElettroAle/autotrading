# language: it
@R0.1.1 @wip
Funzionalità: R0.1.1 Accesso riservato agli utenti con il ruolo Utente
  Come persona censita nella directory aziendale
  Voglio entrare nella piattaforma solo se mi è stato assegnato il ruolo Utente
  Perché l'accesso sia deciso esclusivamente nella directory, senza registrazioni dalla piattaforma

  Fuori ambito: creazione di utenti dalla piattaforma, registrazione autonoma, ruoli diversi da Utente e Gestore chiavi.

  Scenario: Una persona con il ruolo Utente entra nella piattaforma
    Dato che la persona "anna" esiste nella directory con il ruolo "Utente"
    Quando "anna" accede alla piattaforma
    Allora l'accesso di "anna" è consentito
    E la piattaforma identifica "anna" con l'identificativo che la directory le assegna

  Scenario: Una persona senza il ruolo Utente è respinta
    Dato che la persona "bruno" esiste nella directory senza il ruolo "Utente"
    Quando "bruno" accede alla piattaforma
    Allora l'accesso di "bruno" è negato con il motivo "ruolo Utente assente"
    E la piattaforma non crea alcun tenant per "bruno"

  Scenario: Una persona con il solo ruolo Gestore chiavi non entra nella piattaforma
    Dato che la persona "carla" esiste nella directory con il solo ruolo "Gestore chiavi"
    Quando "carla" accede alla piattaforma
    Allora l'accesso di "carla" è negato con il motivo "ruolo Utente assente"

  Scenario: Una richiesta senza identità è respinta
    Quando una richiesta senza identità raggiunge una qualunque funzione della piattaforma
    Allora la richiesta senza identità è respinta come non autenticata

  Scenario: La revoca del ruolo nella directory toglie l'accesso
    Dato che la persona "anna" ha avuto accesso con il ruolo "Utente"
    E che nella directory a "anna" viene tolto il ruolo "Utente"
    Quando "anna" accede di nuovo alla piattaforma con una nuova identità emessa dalla directory
    Allora l'accesso di "anna" è negato con il motivo "ruolo Utente assente"
