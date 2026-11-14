# language: it
@R2.3.1
Funzionalità: R2.3.1 Gestione dei conti dalla dashboard
  Come utente
  Voglio registrare, aggiornare e rimuovere i miei conti dalla dashboard
  Perché non debba usare l'interfaccia programmatica

  Dalla dashboard l'utente registra un conto, ne sostituisce le credenziali e lo rimuove, con le stesse
  regole dell'interfaccia programmatica (R0.2.1, R0.2.4, R0.2.5, R1.1.8). Le credenziali si inseriscono in
  campi che non le mostrano e non compaiono mai nelle pagine dopo l'invio (R0.2.3). Ogni errore
  dell'interfaccia programmatica si mostra con il suo motivo.

  Fuori ambito: la rotazione della chiave di cifratura.

  Contesto:
    Dato che "anna" è nella pagina dei conti

  Scenario: Registrazione di un conto
    Quando "anna" registra il conto "principale" su testnet con indirizzo e chiave dell'API wallet validi
    Allora il conto "principale" compare nell'elenco con il suo saldo
    E la chiave non è visibile in alcuna pagina

  Scenario: Credenziali rifiutate
    Quando "anna" registra un conto con una chiave che l'exchange rifiuta
    Allora la dashboard mostra il motivo del rifiuto
    E il conto non compare nell'elenco

  Scenario: Sostituzione delle credenziali
    Dato che "anna" ha il conto "principale"
    Quando "anna" sostituisce le credenziali del conto "principale" con credenziali valide
    Allora la dashboard conferma la sostituzione

  Scenario: Rimozione con conferma
    Dato che "anna" ha il conto "secondario" senza flussi
    Quando "anna" rimuove il conto "secondario" e conferma
    Allora il conto "secondario" non compare più nell'elenco

  Scenario: Rimozione di un conto con flussi
    Dato che il conto "principale" ha il flusso attivo "alfa"
    Quando "anna" chiede di rimuovere il conto "principale"
    Allora la conferma dice che cosa accade al flusso "alfa" (R1.1.8)
