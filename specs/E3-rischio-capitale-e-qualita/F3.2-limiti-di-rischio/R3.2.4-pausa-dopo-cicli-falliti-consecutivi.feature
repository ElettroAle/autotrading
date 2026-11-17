# language: it
@R3.2.4
Funzionalità: R3.2.4 Pausa dopo cicli falliti consecutivi
  Come utente
  Voglio poter mettere in pausa da solo un flusso i cui cicli falliscono più volte di fila
  Perché un flusso che non riesce a decidere non continua a fallire e a notificare all'infinito

  Ogni flusso può avere un numero massimo di cicli falliti consecutivi, un intero da 1 a 100, assente se non
  indicato. Senza questo valore il flusso continua a provare a ogni ciclo, come oggi.
  Quando i cicli falliti di fila raggiungono il numero, il flusso va in pausa con il motivo
  "<N> cicli falliti consecutivi: <ultimo errore>" e l'utente riceve la notifica di pausa automatica (R1.8.2).
  Un ciclo riuscito azzera il conteggio. La ripresa del flusso (R1.1.4) azzera il conteggio.
  Le posizioni aperte restano aperte, con i loro ordini di protezione (R3.1.2).
  Modificare il valore crea una versione della configurazione (R1.1.3); il valore si può anche togliere.
  Fuori ambito: gli errori permanenti, che mettono già in pausa il flusso al primo ciclo (R1.2.4).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC" e al massimo 3 cicli falliti consecutivi

  Scenario: Pausa al terzo ciclo fallito di fila
    Dato che gli ultimi 2 cicli di "alfa" sono falliti
    Quando il ciclo successivo di "alfa" fallisce con "timeout del modello"
    Allora il flusso "alfa" è in pausa con motivo "3 cicli falliti consecutivi: timeout del modello"
    E "anna" riceve la notifica "⏸️ alfa: in pausa" con le righe "Motivo: 3 cicli falliti consecutivi: timeout del modello"

  Scenario: Un ciclo riuscito azzera il conteggio
    Dato che gli ultimi 2 cicli di "alfa" sono falliti
    Quando il ciclo successivo di "alfa" riesce e i 2 cicli seguenti falliscono
    Allora il flusso "alfa" resta attivo

  Scenario: Flusso senza il massimo
    Dato che "anna" ha il flusso "beta" attivo senza massimo di cicli falliti consecutivi
    Quando 10 cicli di "beta" falliscono di fila
    Allora il flusso "beta" resta attivo

  Scenario: La ripresa azzera il conteggio
    Dato che il flusso "alfa" è in pausa per 3 cicli falliti consecutivi
    Quando "anna" riprende il flusso "alfa" e i 2 cicli seguenti falliscono
    Allora il flusso "alfa" resta attivo

  Scenario: Le posizioni restano aperte
    Dato che "alfa" ha una posizione aperta su "BTC" e gli ultimi 2 cicli di "alfa" sono falliti
    Quando il ciclo successivo di "alfa" fallisce
    Allora la posizione di "alfa" su "BTC" resta aperta

  Scenario: Il massimo si toglie dalla modifica
    Quando "anna" toglie il massimo di cicli falliti consecutivi di "alfa"
    E 5 cicli di "alfa" falliscono di fila
    Allora il flusso "alfa" non ha il massimo di cicli falliti consecutivi
    E il flusso "alfa" resta attivo

  Schema dello scenario: Massimo fuori dall'intervallo
    Quando "anna" imposta il massimo di cicli falliti consecutivi di "alfa" a <valore>
    Allora la modifica viene rifiutata con "il massimo di cicli falliti consecutivi va da 1 a 100"
    Esempi:
      | valore |
      | 0      |
      | 101    |
