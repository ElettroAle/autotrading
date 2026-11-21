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

  Scenario: Piano tra le posizioni aperte della dashboard
    Dato che "alfa" ha aperto long su "BTC" con obiettivo 63000, stop 58500 e invalidazione "chiusura a 4 ore sotto 59000"
    Quando "anna" apre le posizioni aperte di "alfa" nella dashboard
    Allora la posizione su "BTC" mostra obiettivo 63000, stop 58500 e invalidazione "chiusura a 4 ore sotto 59000"

  Scenario: Piano nel dettaglio del ciclo
    Dato che "alfa" ha aperto long su "BTC" con obiettivo 63000 e stop 58500
    Quando "anna" apre nella dashboard il dettaglio del ciclo dell'apertura
    Allora la decisione su "BTC" mostra obiettivo 63000 e stop 58500
