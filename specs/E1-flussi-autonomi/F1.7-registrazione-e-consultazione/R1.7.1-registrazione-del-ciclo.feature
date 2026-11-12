# language: it
@R1.7.1
Funzionalità: R1.7.1 Registrazione completa del ciclo
  Come utente
  Voglio che ogni ciclo sia registrato con tutto ciò che lo ha prodotto
  Perché ogni decisione sia ricostruibile a posteriori con il suo contesto e la sua configurazione

  Per ogni ciclo si registrano: utente, flusso, conto, ambiente, istante previsto e istante effettivo, esito
  (concluso, fallito, saltato), versione della configurazione in vigore, fornitore e modello IA, pesi delle
  fonti, dati raccolti e fonti assenti, contesto integrale inviato all'agente, risposta integrale, decisioni
  interpretate, esito del rischio per ogni decisione (approvata, ridotta, bloccata, scartata), ordini con il
  loro esito reale, costo della chiamata al modello e istantanea dello stato del flusso a fine ciclo.
  Un ciclo fallito registra ciò che ha prodotto fino al passo dell'errore.
  Le credenziali non compaiono mai nella registrazione.

  Fuori ambito: l'interrogazione dello storico per periodo, asset o configurazione.

  Contesto:
    Dato che "anna" ha il flusso "alfa" alla versione di configurazione 3 con modello "openrouter/deepseek-chat"

  Scenario: Ciclo concluso registrato per intero
    Quando il flusso "alfa" esegue un ciclo concluso con un'apertura su "BTC"
    Allora il ciclo registrato contiene:
      | elemento                                  |
      | utente, flusso, conto e ambiente          |
      | istante previsto e istante effettivo      |
      | esito concluso                            |
      | versione di configurazione 3              |
      | modello openrouter/deepseek-chat          |
      | pesi delle fonti                          |
      | dati raccolti                             |
      | contesto integrale inviato all'agente     |
      | risposta integrale dell'agente            |
      | decisioni interpretate                    |
      | esito del rischio per ogni decisione      |
      | ordine su BTC con il suo esito reale      |
      | costo della chiamata al modello           |
      | istantanea dello stato del flusso         |

  Scenario: Ciclo fallito registrato fino all'errore
    Dato che il fornitore IA non risponde
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registrato ha esito fallito al passo "decisione dell'agente"
    E il ciclo registrato contiene i dati raccolti e il contesto inviato all'agente
    E il ciclo registrato non contiene decisioni né ordini

  Scenario: Ciclo saltato registrato
    Dato che il ciclo delle 10:22:00 del flusso "alfa" è saltato perché il precedente era in corso
    Quando "anna" consulta i cicli del flusso "alfa"
    Allora il ciclo delle 10:22:00 compare con esito saltato
