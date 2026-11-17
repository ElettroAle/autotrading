# language: it
@R1.4.6
Funzionalità: R1.4.6 Costo delle chiamate al modello
  Come utente
  Voglio conoscere il costo di ogni chiamata al modello e il totale per flusso
  Perché confronti quanto mi costa ogni flusso

  Per ogni chiamata al modello si registrano token in ingresso, token in uscita e costo in USD, con il ciclo e
  il flusso. Il costo è quello riportato dal fornitore; se il fornitore non lo riporta, si calcola dai prezzi
  del catalogo, e se neppure quelli sono noti il costo si registra come non disponibile.
  Per ogni flusso è consultabile il costo totale dall'avvio e per giorno UTC.
  Anche una chiamata che il ciclo non può usare registra l'uso riportato dal fornitore; una chiamata partita di cui
  nessuno conosce il costo conta tra le chiamate senza costo noto (Bug 541).
  Un errore temporaneo del fornitore (non raggiungibile, tempo scaduto, troppe richieste, errore del fornitore o del
  modello che gli sta dietro, risposta arrivata ma illeggibile) si ritenta nello stesso ciclo fino a 2 volte, con attese di 5 e 15 secondi, anche se la
  chiamata può essere stata addebitata: il ciclo registra il costo di tutti i tentativi e, se nessuno riesce, il
  motivo dell'ultimo. Una chiave rifiutata o un credito esaurito non si ritentano (Bug 583).

  Fuori ambito: limiti di spesa sulla piattaforma, stima del costo prima del salvataggio della configurazione.

  Contesto:
    Dato che "anna" ha il flusso "alfa"

  Scenario: Costo riportato dal fornitore
    Dato che il fornitore riporta per la chiamata 2000 token in ingresso, 500 in uscita e costo 0,0031 USD
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra 2000 token in ingresso, 500 in uscita e costo 0,0031 USD

  Scenario: Costo calcolato dai prezzi del catalogo
    Dato che il fornitore non riporta il costo e riporta 1000 token in ingresso e 1000 in uscita
    E che il catalogo prezza il modello 1 USD per milione di token in ingresso e 2 USD per milione in uscita
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra costo 0,003 USD

  Scenario: Costo non disponibile
    Dato che né il fornitore né il catalogo riportano il prezzo
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra il costo come non disponibile

  Scenario: Totale per flusso
    Dato che il flusso "alfa" ha registrato 3 cicli con costo 0,01 USD ciascuno, 2 ieri e 1 oggi
    Quando "anna" consulta il costo del flusso "alfa"
    Allora il costo totale dall'avvio è 0,03 USD
    E il costo di ieri è 0,02 USD e quello di oggi 0,01 USD

  Scenario: Chiamata pagata senza risposta utilizzabile
    Dato che il fornitore riporta per la chiamata 3000 token in ingresso, 4000 in uscita e costo 0,002 USD senza testo di risposta
    Quando il ciclo del flusso "alfa" chiede la decisione all'agente
    Allora il ciclo fallisce nel passo della decisione dell'agente
    E il fornitore riceve 3 chiamate con attese di 5 e 15 secondi
    E il ciclo registra 9000 token in ingresso, 12000 in uscita e costo 0,006 USD

  Scenario: Chiamata senza risposta dal fornitore
    Dato che il fornitore non risponde entro il tempo massimo
    Quando il ciclo del flusso "alfa" chiede la decisione all'agente
    Allora il ciclo fallisce nel passo della decisione dell'agente
    E il costo del flusso conta una chiamata senza costo noto

  Scenario: Errore temporaneo del fornitore superato con un nuovo tentativo
    Dato che il fornitore risponde alla prima chiamata con l'errore temporaneo "502 Provider returned error" riportando 100 token in ingresso, 0 in uscita e costo 0,0001 USD
    E che il fornitore riporta per la chiamata 2000 token in ingresso, 500 in uscita e costo 0,0031 USD
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo si conclude con la decisione dell'agente
    E il fornitore riceve 2 chiamate con attese di 5 secondi
    E il ciclo registra 2100 token in ingresso, 500 in uscita e costo 0,0032 USD

  Scenario: Errore temporaneo del fornitore a ogni tentativo
    Dato che il fornitore risponde a ogni chiamata con l'errore temporaneo "502 Provider returned error" riportando 100 token in ingresso, 0 in uscita e costo 0,0001 USD
    Quando il ciclo del flusso "alfa" chiede la decisione all'agente
    Allora il ciclo fallisce nel passo della decisione dell'agente con il motivo "502 Provider returned error"
    E il fornitore riceve 3 chiamate con attese di 5 e 15 secondi
    E il ciclo registra 300 token in ingresso, 0 in uscita e costo 0,0003 USD

  Schema dello scenario: Errore permanente del fornitore senza nuovi tentativi
    Dato che il fornitore <errore>
    Quando il ciclo del flusso "alfa" chiede la decisione all'agente
    Allora il ciclo fallisce nel passo della decisione dell'agente
    E il fornitore riceve 1 chiamata senza attese

    Esempi:
      | errore                       |
      | rifiuta la chiave            |
      | dichiara il credito esaurito |
