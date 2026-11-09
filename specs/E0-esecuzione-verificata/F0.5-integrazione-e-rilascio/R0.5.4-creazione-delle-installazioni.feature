# language: it
@R0.5.4 @pipeline
Funzionalità: R0.5.4 Creazione delle installazioni dev e prod dalla pipeline
  Come proprietario
  Voglio creare le macchine delle installazioni dev e prod con un'esecuzione manuale della pipeline e una configurazione versionata
  Perché le due installazioni siano identiche, ricreabili e mai configurate a mano

  Ogni installazione ha la propria macchina. Il nome pubblico è derivato dall'indirizzo della macchina e ha un certificato HTTPS valido.

  Fuori ambito: backup (non serve in E0), dominio personalizzato, configurazione dei segreti applicativi e delle chiavi delle credenziali.

  Schema dello scenario: Creazione di un'installazione
    Dato che l'installazione "<ambiente>" non esiste
    Quando il proprietario avvia la creazione dell'installazione "<ambiente>"
    Allora esiste una macchina dedicata all'installazione "<ambiente>"
    E la macchina accetta connessioni solo sulle porte 22 e 443
    E l'accesso amministrativo è possibile solo con chiave, mai con password
    E il nome pubblico dell'installazione risponde in HTTPS con un certificato valido

    Esempi:
      | ambiente |
      | dev      |
      | prod     |

  Scenario: Ripetere la creazione non duplica l'installazione
    Dato che l'installazione "dev" esiste
    Quando il proprietario avvia di nuovo la creazione dell'installazione "dev"
    Allora l'esecuzione termina indicando "installazione dev già esistente"
    E esiste una sola macchina per l'installazione "dev"

  Scenario: La creazione di un'installazione non tocca l'altra
    Dato che l'installazione "prod" esiste
    Quando il proprietario avvia la creazione dell'installazione "dev"
    Allora la macchina dell'installazione "prod" resta invariata
