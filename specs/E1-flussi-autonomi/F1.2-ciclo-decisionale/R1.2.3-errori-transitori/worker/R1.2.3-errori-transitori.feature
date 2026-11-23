# language: it
@R1.2.3
Funzionalità: R1.2.3 Ciclo fallito per un errore transitorio
  Come utente
  Voglio che un errore transitorio faccia fallire solo il ciclo in cui avviene
  Perché un problema momentaneo non fermi il flusso né tocchi gli altri flussi

  Un errore transitorio è un errore che può non ripetersi al ciclo successivo: rete non raggiungibile, fornitore
  IA o exchange momentaneamente indisponibile, tempo di risposta scaduto.
  Un errore transitorio di un passo del ciclo si ritenta nello stesso ciclo, fino a 2 volte con attese di 5 e 15 secondi
  (Bug 718). Il fornitore IA ha i propri tentativi, fino a 3 volte con attese di 2, 8 e 30 secondi (R1.4.6, R1.4.9,
  Bug 583). Di un ordine si ritenta il solo invio fallito, mai gli ordini già eseguiti, e un ordine ritentato non si apre
  mai due volte. Ogni tentativo fallito si registra nel ciclo con il passo, il numero del tentativo e l'errore.
  Se nessun tentativo riesce il ciclo si interrompe nel punto dell'errore: nessun ordine successivo all'errore viene
  inviato. Il ciclo si registra come fallito con il passo, il tipo di errore e il messaggio originale.
  Una fonte dati che non risponde non si ritenta e non fa fallire il ciclo (R1.2.5).
  Il flusso resta attivo e il ciclo successivo parte al proprio istante. Gli altri flussi non ne risentono.

  Fuori ambito: gli errori permanenti (R1.2.4), la notifica del ciclo fallito (R1.8.2).

  Contesto:
    Dato che "anna" ha i flussi "alfa" e "beta" attivi

  Schema dello scenario: Ciclo fallito senza ordini
    Dato che <sistema> non risponde durante il passo "<passo>" del ciclo del flusso "alfa"
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo è registrato come fallito al passo "<passo>" con il tipo di errore e il messaggio originale
    E il ciclo non invia ordini all'exchange
    E il flusso "alfa" è nello stato "attivo"

    Esempi:
      | sistema              | passo                          |
      | l'exchange           | lettura dello stato del flusso |
      | il fornitore IA      | decisione dell'agente          |

  Scenario: Il ciclo successivo parte regolarmente
    Dato che il ciclo delle 10:07:00 del flusso "alfa" è fallito per un errore transitorio
    Quando arrivano le 10:22:00
    Allora il flusso "alfa" esegue il ciclo delle 10:22:00

  Scenario: Gli altri flussi non ne risentono
    Dato che il ciclo del flusso "alfa" fallisce per un errore transitorio
    Quando i flussi "alfa" e "beta" eseguono un ciclo
    Allora il ciclo del flusso "beta" si conclude regolarmente

  Scenario: Errore durante l'esecuzione degli ordini
    Dato che l'agente decide di aprire su "BTC" e su "ETH"
    E che l'exchange non risponde all'ordine su "BTC"
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo è registrato come fallito al passo "esecuzione degli ordini"
    E l'ordine su "ETH" non viene inviato

  Scenario: Errore temporaneo ritentato nello stesso ciclo
    Dato che l'exchange non risponde una volta durante il passo "lettura dello stato del flusso" del ciclo del flusso "alfa"
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo del flusso "alfa" si conclude regolarmente
    E lo stato del flusso "alfa" è letto 2 volte
    E il ciclo attende 5 secondi prima del nuovo tentativo
    E il ciclo registra il tentativo 1 fallito al passo "lettura dello stato del flusso" con il messaggio originale

  Scenario: Tre errori temporanei dello stesso passo fanno fallire il ciclo
    Dato che l'exchange non risponde durante il passo "lettura dello stato del flusso" del ciclo del flusso "alfa"
    Quando il flusso "alfa" esegue un ciclo
    Allora lo stato del flusso "alfa" è letto 3 volte
    E il ciclo attende 5 e poi 15 secondi prima dei nuovi tentativi
    E il ciclo registra i tentativi 1, 2 e 3 falliti al passo "lettura dello stato del flusso"
    E il ciclo è registrato come fallito al passo "lettura dello stato del flusso" con il tipo di errore e il messaggio originale
    E il flusso "alfa" è nello stato "attivo"

  Scenario: Un errore permanente non si ritenta
    Dato che l'exchange rifiuta le credenziali del conto "test-1"
    Quando il flusso "alfa" esegue un ciclo
    Allora lo stato del flusso "alfa" è letto una sola volta
    E il ciclo non attende nuovi tentativi
    E il flusso "alfa" è nello stato "in pausa"
