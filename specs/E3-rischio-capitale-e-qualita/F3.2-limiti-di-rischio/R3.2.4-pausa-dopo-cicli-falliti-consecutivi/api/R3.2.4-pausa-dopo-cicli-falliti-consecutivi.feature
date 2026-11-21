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

  Schema dello scenario: Massimo fuori dall'intervallo
    Quando "anna" imposta il massimo di cicli falliti consecutivi di "alfa" a <valore>
    Allora la modifica viene rifiutata con "il massimo di cicli falliti consecutivi va da 1 a 100"
    Esempi:
      | valore |
      | 0      |
      | 101    |
