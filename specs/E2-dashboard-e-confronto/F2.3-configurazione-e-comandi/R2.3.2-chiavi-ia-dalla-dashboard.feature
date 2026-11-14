# language: it
@R2.3.2
Funzionalità: R2.3.2 Chiavi dei fornitori IA dalla dashboard
  Come utente
  Voglio gestire le mie chiavi dei fornitori IA dalla dashboard
  Perché colleghi i modelli che voglio usare

  Dalla dashboard l'utente registra, sostituisce e rimuove la chiave di un fornitore IA, con le regole di
  R1.4.1 (nessuna verifica alla registrazione). La chiave non è mai mostrata dopo l'invio: l'elenco mostra
  solo il fornitore e la data di registrazione.

  Fuori ambito: la verifica della chiave alla registrazione.

  Contesto:
    Dato che "anna" è nella pagina delle chiavi IA

  Scenario: Registrazione di una chiave
    Quando "anna" registra una chiave per "openrouter"
    Allora l'elenco mostra "openrouter" con la data di registrazione
    E la chiave non è visibile in alcuna pagina

  Scenario: Sostituzione di una chiave
    Dato che "anna" ha una chiave per "openrouter"
    Quando "anna" la sostituisce
    Allora l'elenco mostra la nuova data di registrazione

  Scenario: Rimozione di una chiave
    Dato che "anna" ha una chiave per "openrouter"
    Quando "anna" la rimuove e conferma
    Allora "openrouter" non compare più nell'elenco
