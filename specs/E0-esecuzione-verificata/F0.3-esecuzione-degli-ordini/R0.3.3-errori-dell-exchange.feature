# language: it
@R0.3.3 @wip
Funzionalità: R0.3.3 Gestione degli errori dell'exchange sugli ordini
  Come utente
  Voglio che un ordine rifiutato dall'exchange sia riportato e registrato senza fermare la piattaforma
  Perché sappia esattamente cosa è successo e la piattaforma continui a funzionare

  Un ordine rifiutato non viene ritentato automaticamente.

  Fuori ambito: nuovi tentativi automatici, notifiche (arrivano con le notifiche).

  Contesto:
    Dato che il conto "test-1" è su "Hyperliquid"

  Schema dello scenario: Ordine rifiutato dall'exchange
    Dato che l'exchange rifiuta l'ordine con il messaggio "<messaggio>"
    Quando la piattaforma invia un ordine sul conto "test-1"
    Allora l'esito dell'ordine è "rifiutato" con il motivo "<motivo>"
    E l'esito riporta il messaggio originale "<messaggio>"
    E l'ordine rifiutato è registrato con il suo identificativo della piattaforma
    E la piattaforma non ritenta l'ordine
    E la piattaforma accetta le richieste successive

    Esempi:
      | messaggio                          | motivo                        |
      | Order must have minimum value $10  | importo sotto il minimo       |
      | Insufficient margin                | margine insufficiente         |
      | Unknown asset                      | asset non disponibile         |

  Scenario: Messaggio dell'exchange non riconosciuto
    Dato che l'exchange rifiuta l'ordine con un messaggio che la piattaforma non riconosce
    Quando la piattaforma invia un ordine sul conto "test-1"
    Allora l'esito dell'ordine è "rifiutato" con il motivo "rifiuto dell'exchange"
    E l'esito riporta il messaggio originale dell'exchange

  Scenario: Nessuna risposta dall'exchange all'invio
    Dato che l'exchange non risponde entro 10 secondi all'invio di un ordine
    Quando la piattaforma invia un ordine sul conto "test-1"
    Allora la piattaforma cerca sull'exchange l'ordine tramite il suo identificativo
    E l'esito dell'ordine è quello trovato sull'exchange, oppure "esito sconosciuto" se l'ordine non risulta
    E l'esito "esito sconosciuto" è registrato e riportato
