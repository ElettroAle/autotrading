# language: it
@R2.5.1
Funzionalità: R2.5.1 Storico interrogabile
  Come utente
  Voglio interrogare lo storico dei miei flussi con dei filtri
  Perché ritrovi cicli, posizioni e ordini di un periodo, un asset o una configurazione

  L'utente interroga tre storici: cicli, posizioni chiuse, ordini con le loro esecuzioni. Ogni storico si
  filtra per flusso, conto, periodo, asset e versione della configurazione, in combinazione (RF-20.04). Il
  filtro per versione vale per un solo flusso. I risultati sono dal più recente, a pagine di 50. Ogni
  interrogazione riguarda solo i dati dell'utente. Disponibile dalla dashboard e dall'interfaccia
  programmatica.

  Fuori ambito: la ricerca nel testo del ragionamento dell'agente.

  Contesto:
    Dato che "anna" ha il flusso "alfa" sul conto "principale" con cicli dal 1° al 30 novembre e la versione 2 in vigore dal 15 novembre
    E che il flusso "alfa" ha ordini e posizioni chiuse su "BTC" e "ETH"
    E che "bruno" ha il flusso "omega"

  Scenario: Cicli di una versione
    Quando "anna" interroga i cicli del flusso "alfa" con la versione 2
    Allora ottiene solo i cicli dal 15 novembre in poi

  Scenario: Posizioni chiuse per asset e periodo
    Quando "anna" interroga le posizioni chiuse con asset "ETH" dal 10 al 20 novembre
    Allora ottiene solo le posizioni su "ETH" chiuse in quel periodo

  Scenario: Ordini ed esecuzioni per conto
    Quando "anna" interroga gli ordini del conto "principale"
    Allora ogni ordine mostra le sue esecuzioni con prezzo, quantità e commissioni

  Scenario: Versione senza flusso
    Quando "anna" interroga i cicli con la versione 2 senza indicare un flusso
    Allora l'interrogazione è rifiutata con il motivo "la versione richiede un flusso"

  Scenario: Solo i dati dell'utente
    Quando "bruno" interroga le posizioni chiuse con asset "BTC"
    Allora non ottiene alcuna posizione del flusso "alfa"
