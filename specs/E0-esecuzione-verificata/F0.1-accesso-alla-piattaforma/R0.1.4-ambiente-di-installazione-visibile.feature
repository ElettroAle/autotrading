# language: it
@R0.1.4
Funzionalità: R0.1.4 Ambiente di installazione sempre riconoscibile
  Come utente
  Voglio sapere sempre se sto usando l'installazione "dev" o "prod"
  Perché non confonda l'ambiente collegato agli exchange di test con quello collegato ai fondi reali

  Fuori ambito: scelta dell'exchange di test o reale per singolo conto (dipende solo dalla configurazione dell'installazione).

  Schema dello scenario: Ogni risposta riporta il nome dell'ambiente
    Dato che l'installazione è configurata con l'ambiente "<ambiente>"
    Quando un utente riceve una qualunque risposta dalla piattaforma
    Allora la risposta riporta il nome dell'ambiente "<ambiente>"

    Esempi:
      | ambiente |
      | dev      |
      | prod     |

  Scenario: L'installazione non parte senza ambiente dichiarato
    Dato che la configurazione dell'installazione non dichiara l'ambiente
    Quando l'installazione viene avviata
    Allora l'avvio fallisce con il motivo "ambiente non dichiarato"

  Scenario: L'installazione non parte con un ambiente sconosciuto
    Dato che la configurazione dell'installazione dichiara l'ambiente "staging"
    Quando l'installazione viene avviata
    Allora l'avvio fallisce con il motivo "ambiente non ammesso: sono ammessi dev e prod"
