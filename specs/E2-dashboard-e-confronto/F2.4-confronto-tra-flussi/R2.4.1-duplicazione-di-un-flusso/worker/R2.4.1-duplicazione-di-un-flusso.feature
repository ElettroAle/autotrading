# language: it
@R2.4.1
Funzionalità: R2.4.1 Duplicazione di un flusso
  Come utente
  Voglio duplicare un flusso per crearne una variante
  Perché confronti due strategie che differiscono in un solo punto

  La duplicazione crea un nuovo flusso nello stato "bozza" (RF-03.05) con la strategia dell'originale
  (intervallo, fonti con pesi e parametri, modello con i suoi parametri, istruzioni e regole di rischio), il
  suo conto e il suo capitale allocato, e nessun asset: due flussi sullo stesso conto non hanno asset in comune
  (RF-02.05). Il nome è quello dell'originale seguito da " (copia)". Una bozza non esegue cicli e non impegna
  capitale. Finché il flusso è una bozza, conto, capitale allocato e asset si impostano nella sua
  configurazione e si salvano con lei; l'avvio di una bozza verifica che conto, capitale e almeno un asset ci
  siano e che nessun asset sia già usato da un altro flusso sullo stesso conto (RF-02.05, R1.1.2), poi il
  flusso diventa attivo. Nella dashboard Avvia resta disattivato finché manca qualcosa, con accanto l'elenco di ciò
  che manca e il rimando "Configura" alla configurazione del flusso (Bug 560). La copia ha storia propria e parte
  dalla versione 1. Disponibile dalla dashboard e dall'interfaccia programmatica.

  Fuori ambito: la copia dei cicli o delle posizioni dell'originale.

  Contesto:
    Dato che "anna" ha il flusso "alfa" sul conto "principale" con asset "BTC", fonti "indicatori" peso 2 e modello "openrouter/deepseek-chat"
    E che "anna" ha anche il conto "secondario"

  Scenario: Una bozza non esegue cicli
    Dato che "anna" ha duplicato il flusso "alfa"
    Quando passa un intervallo intero del flusso "alfa (copia)"
    Allora il flusso "alfa (copia)" non ha cicli
    E il capitale libero del conto "principale" non cambia
