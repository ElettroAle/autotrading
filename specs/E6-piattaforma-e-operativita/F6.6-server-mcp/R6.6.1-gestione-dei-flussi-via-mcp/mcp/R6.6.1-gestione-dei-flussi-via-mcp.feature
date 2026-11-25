# language: it
@R6.6.1
Funzionalità: R6.6.1 Gestione dei flussi via MCP
  Come utente
  Voglio consultare e gestire i miei flussi da un client IA che parla MCP
  Perché posso chiedere stato, risultati e decisioni e operare sui flussi in linguaggio naturale senza aprire la dashboard

  Un server MCP espone i dati dell'utente (flussi e loro stato, posizioni aperte e chiuse, cicli e decisioni, statistiche
  e classifica) e le stesse operazioni sui flussi dell'API (crea, importa, duplica, modifica, avvia e pausa, ferma,
  archivia, incassa, cambia capitale, ciclo a richiesta, riprendi aperture), con gli stessi casi d'uso e le stesse
  regole. L'utente si autentica con Entra (client preregistrato) e vede solo i dati del suo tenant. Raggiungibile solo
  dalla tailnet. Nessuno strumento legge o modifica credenziali.

  Contesto:
    Dato che "anna" ha i flussi "alfa" e "beta" e "bruno" ha il flusso "gamma"

  Scenario: Elenco dei flussi
    Dato che "anna" ha collegato un client MCP con il suo accesso Entra
    Quando il client chiede l'elenco dei flussi
    Allora riceve "alfa" e "beta" con stato, valore e PnL dall'avvio

  Scenario: Dati di un flusso
    Quando il client di "anna" chiede posizioni, cicli e statistiche del flusso "alfa"
    Allora riceve gli stessi valori che la dashboard mostra per "alfa"

  Scenario: Modifica di un flusso
    Quando il client di "anna" mette in pausa il flusso "alfa"
    Allora il flusso "alfa" risulta in pausa come se l'avesse fatto dalla dashboard

  Scenario: Stesse regole dell'API
    Quando il client di "anna" cambia il capitale del flusso "alfa" oltre il saldo del conto
    Allora riceve lo stesso errore che l'API restituisce

  Scenario: Isolamento tra tenant
    Quando il client di "anna" chiede o modifica il flusso "gamma"
    Allora riceve l'errore "flusso non trovato"

  Scenario: Client senza accesso
    Quando un client MCP senza token valido chiede l'elenco dei flussi
    Allora la richiesta è rifiutata come non autenticata

  Scenario: Nessuna credenziale
    Quando il client di "anna" elenca gli strumenti disponibili
    Allora nessuno strumento legge o modifica le credenziali di un conto, di una fonte o di un fornitore IA

  Scenario: La risorsa del server MCP è un identificativo dell'applicazione dell'API
    Dato un'installazione con il server MCP su "https://<nome>/mcp"
    Quando lo script delle impostazioni Entra gira per l'installazione
    Allora l'applicazione dell'API ha tra i suoi identificativi "https://<nome>/mcp"
    E conserva l'identificativo "api://<client id>"

  Scenario: Il client MCP accetta il ritorno sulla porta locale del client
    Quando lo script delle impostazioni Entra gira per l'installazione
    Allora il client MCP ha come unico redirect "http://localhost/callback"

  Scenario: Lo script è idempotente
    Dato un'installazione già configurata
    Quando lo script gira di nuovo
    Allora identificativi e redirect non cambiano
