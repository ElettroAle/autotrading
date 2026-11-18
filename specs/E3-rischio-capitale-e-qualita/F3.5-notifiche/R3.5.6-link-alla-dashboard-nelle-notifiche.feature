# language: it
@R3.5.6
Funzionalità: R3.5.6 Link alla dashboard nelle notifiche
  Come utente
  Voglio aprire dalla notifica la pagina che la riguarda
  Perché voglio vedere subito il flusso o l'operazione senza cercarli

  Un'operazione porta alla scheda del flusso (Posizioni o Posizioni chiuse) con la posizione evidenziata, più il link
  al flusso; su Telegram pulsanti sotto il messaggio, nell'email link in fondo. Gli eventi di un conto portano al
  dettaglio del loro avviso (R6.2.3).

  Scenario: Notifica di un flusso
    Dato un flusso "prova-btc" con un ciclo fallito
    Quando ricevo la notifica del ciclo fallito
    Allora la notifica porta alla pagina del flusso "prova-btc"

  Schema dello scenario: Notifica di un'operazione
    Dato un flusso "prova-btc" con l'evento "<evento>" su una posizione
    Quando ricevo la notifica
    Allora la notifica porta alla scheda "<scheda>" del flusso con quella posizione evidenziata
    E porta anche alla pagina del flusso

    Esempi:
      | evento                        | scheda           |
      | apertura di una posizione     | Posizioni        |
      | chiusura di una posizione     | Posizioni chiuse |
      | stop loss attivato            | Posizioni chiuse |
      | take profit attivato          | Posizioni chiuse |
      | liquidazione di una posizione | Posizioni chiuse |

  Scenario: Notifica di un conto
    Dato una posizione non attribuibile sul conto "Hyperliquid testnet"
    Quando ricevo la notifica
    Allora la notifica porta al dettaglio del suo avviso

  Scenario: Pulsanti su Telegram e link nell'email
    Dato una notifica con i link al flusso e all'operazione
    Quando arriva su Telegram
    Allora sotto il messaggio ci sono i pulsanti "Apri flusso" e "Apri operazione"
    Quando arriva per email
    Allora i link sono in fondo al testo
