# language: it
@R5.5.6
Funzionalità: R5.5.6 Commissioni nel contesto dell'agente
  Come utente
  Voglio poter dare all'agente il costo di andata e ritorno di un'operazione
  Perché ne tenga conto

  L'agente calcola il rapporto tra guadagno atteso e perdita possibile senza conoscere il costo dell'operazione. Su un
  flusso con molte operazioni brevi le commissioni sono state circa il 72% della perdita chiusa (revisione del 25
  novembre 2026).

  Impostazione del flusso: commissioni nel contesto dell'agente, opzione spenta di default. Spenta, l'agente riceve ciò
  che riceve oggi.

  Regole.
  - Con l'opzione accesa lo stato inviato all'agente riporta il costo di andata e ritorno in percentuale del valore della
    posizione: la commissione che l'exchange applica al conto per un ordine a mercato, contata per l'apertura e per la
    chiusura.
  - Se l'exchange non dà la commissione, il costo di andata e ritorno compare tra i dati mancanti e il ciclo non
    fallisce.

  Fuori ambito: funding, slittamento, commissioni già pagate dal flusso (sono nelle statistiche).

  Scenario: Opzione spenta di default
    Quando "anna" crea il flusso "beta" senza indicare le commissioni nel contesto dell'agente
    Allora il flusso "beta" ha le commissioni nel contesto dell'agente spente

  Scenario: Flussi già esistenti
    Dato che il flusso "alfa" esisteva prima dell'opzione delle commissioni
    Quando "anna" legge la configurazione di "alfa"
    Allora "alfa" ha le commissioni nel contesto dell'agente spente
    E la configurazione di "alfa" resta alla stessa versione

  Scenario: L'opzione crea una versione
    Quando "anna" accende per "alfa" le commissioni nel contesto dell'agente
    Allora "alfa" ha una nuova versione della configurazione con le commissioni nel contesto dell'agente accese
