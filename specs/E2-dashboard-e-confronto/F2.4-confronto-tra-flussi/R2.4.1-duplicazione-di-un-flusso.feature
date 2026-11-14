# language: it
@R2.4.1
Funzionalità: R2.4.1 Duplicazione di un flusso
  Come utente
  Voglio duplicare un flusso per crearne una variante
  Perché confronti due strategie che differiscono in un solo punto

  La duplicazione crea un nuovo flusso nello stato "bozza": un flusso che ha solo la strategia
  dell'originale (intervallo, fonti con pesi e parametri, modello con i suoi parametri, istruzioni e regole
  di rischio) e non ha conto, capitale allocato né asset (RF-03.05). Il nome è quello dell'originale seguito
  da " (copia)". Una bozza non esegue cicli e non impegna capitale. Prima dell'avvio l'utente le assegna
  conto, capitale allocato e asset; l'avvio di una bozza verifica che conto, capitale e almeno un asset ci
  siano e che nessun asset sia già usato da un altro flusso sullo stesso conto (RF-02.05, R1.1.2), poi il
  flusso diventa attivo. La copia ha storia propria e parte dalla versione 1. Disponibile dalla dashboard e
  dall'interfaccia programmatica.

  Fuori ambito: la copia dei cicli o delle posizioni dell'originale.

  Contesto:
    Dato che "anna" ha il flusso "alfa" sul conto "principale" con asset "BTC", fonti "indicatori" peso 2 e modello "openrouter/deepseek-chat"
    E che "anna" ha anche il conto "secondario"

  Scenario: Bozza con la sola strategia
    Quando "anna" duplica il flusso "alfa"
    Allora esiste il flusso "alfa (copia)" nello stato "bozza" alla versione 1
    E ha fonti "indicatori" peso 2 e modello "openrouter/deepseek-chat"
    E non ha conto, capitale allocato né asset

  Scenario: Una bozza non esegue cicli
    Dato che "anna" ha duplicato il flusso "alfa"
    Quando passa un intervallo intero del flusso "alfa (copia)"
    Allora il flusso "alfa (copia)" non ha cicli
    E il capitale libero del conto "principale" non cambia

  Scenario: Avvio dopo aver assegnato conto, capitale e asset
    Dato che "anna" ha duplicato il flusso "alfa"
    Quando "anna" assegna al flusso "alfa (copia)" il conto "secondario", 200 USDC e l'asset "BTC"
    E "anna" avvia il flusso "alfa (copia)"
    Allora il flusso "alfa (copia)" è nello stato "attivo"

  Scenario: Avvio di una bozza incompleta rifiutato
    Dato che "anna" ha duplicato il flusso "alfa"
    Quando "anna" avvia il flusso "alfa (copia)" senza assegnare conto, capitale e asset
    Allora l'avvio è rifiutato con il motivo "conto, capitale allocato e asset mancanti"
    E il flusso "alfa (copia)" resta nello stato "bozza"

  Scenario: Stesso asset sullo stesso conto rifiutato all'avvio
    Dato che "anna" ha duplicato il flusso "alfa"
    Quando "anna" assegna al flusso "alfa (copia)" il conto "principale", 100 USDC e l'asset "BTC"
    E "anna" avvia il flusso "alfa (copia)"
    Allora l'avvio è rifiutato perché "BTC" è già usato dal flusso "alfa" sul conto "principale"
    E il flusso "alfa (copia)" resta nello stato "bozza"

  Scenario: Flusso di un altro utente
    Quando "bruno" chiede di duplicare il flusso "alfa"
    Allora la richiesta è rifiutata come flusso inesistente
