# language: it
@R3.1.1
Funzionalità: R3.1.1 Piano di uscita nella decisione
  Come utente
  Voglio che a ogni apertura l'agente dichiari obiettivo, stop e condizione di invalidazione
  Perché so in anticipo come intende uscire e l'agente lo ritrova nei cicli successivi

  Per un'apertura la decisione dell'agente può contenere il piano di uscita: prezzo obiettivo, prezzo di stop e
  condizione di invalidazione (un testo). Ogni elemento è facoltativo (RF-17.05).
  Un prezzo incoerente con la direzione si scarta e il ciclo ne registra il motivo; l'apertura prosegue senza quel
  livello. Per un long è incoerente uno stop pari o sopra il prezzo di mercato dell'exchange del conto, o un obiettivo
  pari o sotto; per uno short il contrario.
  Il piano si registra con la decisione. Finché la posizione è aperta, il piano in vigore compare nello stato del
  flusso inviato all'agente a ogni ciclo (RF-13.03), nel dettaglio del ciclo e tra le posizioni aperte della
  dashboard (R2.2.4).

  Fuori ambito: gli ordini di protezione sull'exchange (R3.1.2); la modifica del piano di una posizione aperta
  (R3.1.3); la confidenza (R3.1.4).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC"
    E che il prezzo di mercato di "BTC" sull'exchange del conto è 60000

  Scenario: Apertura con piano di uscita completo
    Quando l'agente di "alfa" decide di aprire long su "BTC" con obiettivo 63000, stop 58500 e invalidazione "chiusura a 4 ore sotto 59000"
    Allora la decisione registrata di "alfa" contiene obiettivo 63000, stop 58500 e invalidazione "chiusura a 4 ore sotto 59000"

  Scenario: Apertura senza piano di uscita
    Quando l'agente di "alfa" decide di aprire long su "BTC" senza piano di uscita
    Allora "alfa" apre la posizione su "BTC"
    E la decisione registrata di "alfa" non ha obiettivo né invalidazione

  Schema dello scenario: Livello incoerente con la direzione
    Quando l'agente di "alfa" decide di aprire <direzione> su "BTC" con <livello> <prezzo>
    Allora "alfa" apre la posizione su "BTC" senza quel livello nel piano
    E il ciclo di "alfa" registra "<livello> <prezzo> scartato: incoerente con <direzione> al prezzo 60000"

    Esempi:
      | direzione | livello   | prezzo |
      | long      | stop      | 61000  |
      | long      | stop      | 60000  |
      | long      | obiettivo | 59000  |
      | short     | stop      | 59000  |
      | short     | obiettivo | 61000  |

  Scenario: Il piano torna all'agente nei cicli successivi
    Dato che "alfa" ha aperto long su "BTC" con obiettivo 63000, stop 58500 e invalidazione "chiusura a 4 ore sotto 59000"
    Quando parte il ciclo successivo di "alfa"
    Allora lo stato del flusso inviato all'agente riporta per la posizione su "BTC" obiettivo 63000, stop 58500 e invalidazione "chiusura a 4 ore sotto 59000"
