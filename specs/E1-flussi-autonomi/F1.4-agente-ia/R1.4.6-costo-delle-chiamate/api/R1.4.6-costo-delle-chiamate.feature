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
  modello che gli sta dietro, risposta arrivata ma illeggibile) si ritenta nello stesso ciclo fino a 3 volte, con attese di 2, 8 e 30 secondi, anche
  se la chiamata può essere stata addebitata: il ciclo registra il costo di tutti i tentativi e, se nessuno riesce, il
  motivo dell'ultimo. Una chiave rifiutata o un credito esaurito non si ritentano (Bug 583, R1.4.9).

  Fuori ambito: limiti di spesa sulla piattaforma, stima del costo prima del salvataggio della configurazione.

  Contesto:
    Dato che "anna" ha il flusso "alfa"

  Scenario: Totale per flusso
    Dato che il flusso "alfa" ha registrato 3 cicli con costo 0,01 USD ciascuno, 2 ieri e 1 oggi
    Quando "anna" consulta il costo del flusso "alfa"
    Allora il costo totale dall'avvio è 0,03 USD
    E il costo di ieri è 0,02 USD e quello di oggi 0,01 USD
