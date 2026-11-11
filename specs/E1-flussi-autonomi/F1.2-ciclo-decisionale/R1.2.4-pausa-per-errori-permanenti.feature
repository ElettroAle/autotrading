# language: it
@R1.2.4 @wip
Funzionalità: R1.2.4 Pausa automatica per un errore permanente
  Come utente
  Voglio che un errore che si ripeterebbe a ogni ciclo metta il flusso in pausa
  Perché il flusso non accumuli cicli falliti finché non risolvo il problema

  Un errore permanente è un errore che si ripete a ogni ciclo finché l'utente non interviene: credito esaurito
  presso il fornitore IA, chiave del fornitore IA non valida o revocata, credenziali dell'exchange non valide o
  revocate.
  Il ciclo si interrompe come per un errore transitorio (R1.2.3) e in più il flusso passa allo stato "in pausa",
  con il motivo della pausa automatica. Le posizioni aperte restano sull'exchange.
  Il flusso riparte solo quando l'utente lo riprende (R1.1.4).
  Un errore permanente delle credenziali di un conto mette in pausa tutti i flussi attivi di quel conto;
  un errore permanente del fornitore IA mette in pausa i flussi attivi che usano la chiave di quel fornitore.

  Fuori ambito: la notifica della pausa automatica (R1.8.2).

  Contesto:
    Dato che "anna" ha i flussi "alfa" e "beta" attivi sul conto "test-1" con modelli del fornitore "openrouter"

  Schema dello scenario: Pausa automatica
    Dato che <causa>
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo è registrato come fallito con il motivo "<motivo>"
    E il flusso "alfa" è nello stato "in pausa" con il motivo "<motivo>"

    Esempi:
      | causa                                                  | motivo                                    |
      | il fornitore "openrouter" risponde credito esaurito    | credito esaurito presso openrouter        |
      | il fornitore "openrouter" rifiuta la chiave            | chiave del fornitore non valida: openrouter |
      | l'exchange rifiuta le credenziali del conto "test-1"   | credenziali del conto non valide: test-1  |

  Scenario: Le credenziali del conto mettono in pausa tutti i flussi del conto
    Dato che l'exchange rifiuta le credenziali del conto "test-1"
    Quando il flusso "alfa" esegue un ciclo
    Allora il flusso "beta" è nello stato "in pausa" con il motivo "credenziali del conto non valide: test-1"

  Scenario: La chiave del fornitore mette in pausa i flussi che la usano
    Dato che "anna" ha anche il flusso "gamma" attivo con un modello del fornitore "anthropic"
    E che il fornitore "openrouter" rifiuta la chiave
    Quando il flusso "alfa" esegue un ciclo
    Allora il flusso "beta" è nello stato "in pausa"
    E il flusso "gamma" è nello stato "attivo"

  Scenario: Le posizioni restano aperte
    Dato che il flusso "alfa" ha una posizione aperta su "BTC"
    E che il fornitore "openrouter" risponde credito esaurito
    Quando il flusso "alfa" esegue un ciclo
    Allora la posizione su "BTC" resta aperta sull'exchange
