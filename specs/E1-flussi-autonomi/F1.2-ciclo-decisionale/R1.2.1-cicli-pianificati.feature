# language: it
@R1.2.1 @wip
Funzionalità: R1.2.1 Cicli pianificati
  Come utente
  Voglio che ogni flusso attivo esegua il proprio ciclo decisionale al proprio intervallo, giorno e notte
  Perché l'agente operi in autonomia senza che io intervenga

  Il primo ciclo parte all'avvio del flusso; i successivi ogni intervallo di ciclo da quell'istante.
  Alla ripresa da una pausa il primo ciclo parte alla ripresa e la pianificazione riparte da lì.
  Un ciclo è puntuale se parte entro 60 secondi dall'istante previsto; oltre, il ritardo si registra con il ciclo.
  Ogni ciclo esegue, nell'ordine: lettura dello stato del flusso, raccolta dei dati delle fonti attive,
  composizione del contesto, decisione dell'agente, controllo del rischio, esecuzione degli ordini,
  aggiornamento dello stato del flusso, registrazione del ciclo.
  I flussi sono indipendenti: un flusso lento o in errore non ritarda i cicli degli altri flussi.

  Fuori ambito: la sovrapposizione tra cicli (R1.2.2), la gestione degli errori (R1.2.3, R1.2.4).

  Contesto:
    Dato che "anna" ha il flusso "alfa" con intervallo di ciclo di 15 minuti

  Scenario: Pianificazione dall'avvio
    Quando "anna" avvia il flusso "alfa" alle 10:07:00
    Allora il flusso "alfa" esegue cicli alle 10:07:00, 10:22:00 e 10:37:00

  Scenario: Pianificazione dalla ripresa
    Dato che il flusso "alfa" è stato avviato alle 10:07:00 e messo in pausa alle 10:30:00
    Quando "anna" riprende il flusso "alfa" alle 11:00:00
    Allora il flusso "alfa" esegue cicli alle 11:00:00 e 11:15:00

  Scenario: Ciclo in ritardo
    Dato che il flusso "alfa" ha un ciclo previsto alle 10:22:00
    Quando il ciclo parte alle 10:23:30
    Allora il ciclo è registrato con un ritardo di 90 secondi

  Scenario: Ciclo puntuale
    Dato che il flusso "alfa" ha un ciclo previsto alle 10:22:00
    Quando il ciclo parte alle 10:22:40
    Allora il ciclo è registrato senza ritardo

  Scenario: I passi del ciclo nell'ordine
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra i passi in quest'ordine:
      | passo                               |
      | lettura dello stato del flusso      |
      | raccolta dei dati delle fonti       |
      | composizione del contesto           |
      | decisione dell'agente               |
      | controllo del rischio               |
      | esecuzione degli ordini             |
      | aggiornamento dello stato del flusso |
      | registrazione del ciclo             |

  Scenario: Un flusso lento non ritarda gli altri
    Dato che "anna" ha anche il flusso "beta" con un ciclo previsto alle 10:22:00
    E che il ciclo del flusso "alfa" iniziato alle 10:21:00 è ancora in corso alle 10:22:00
    Quando arrivano le 10:22:00
    Allora il ciclo del flusso "beta" parte puntuale
