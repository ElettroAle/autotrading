# language: it
@R1.2.3
Funzionalità: R1.2.3 Ciclo fallito per un errore transitorio
  Come utente
  Voglio che un errore transitorio faccia fallire solo il ciclo in cui avviene
  Perché un problema momentaneo non fermi il flusso né tocchi gli altri flussi

  Un errore transitorio è un errore che può non ripetersi al ciclo successivo: rete non raggiungibile, fornitore
  IA o exchange momentaneamente indisponibile, tempo di risposta scaduto.
  Il ciclo si interrompe nel punto dell'errore senza nuovi tentativi: nessun ordine successivo all'errore viene
  inviato. Il ciclo si registra come fallito con il passo, il tipo di errore e il messaggio originale.
  Il flusso resta attivo e il ciclo successivo parte al proprio istante. Gli altri flussi non ne risentono.
  Una fonte dati che non risponde non fa fallire il ciclo (R1.2.5).

  Fuori ambito: gli errori permanenti (R1.2.4), la notifica del ciclo fallito (R1.8.2).

  Contesto:
    Dato che "anna" ha i flussi "alfa" e "beta" attivi

  Schema dello scenario: Ciclo fallito senza ordini
    Dato che <sistema> non risponde durante il passo "<passo>" del ciclo del flusso "alfa"
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo è registrato come fallito al passo "<passo>" con il messaggio originale
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
