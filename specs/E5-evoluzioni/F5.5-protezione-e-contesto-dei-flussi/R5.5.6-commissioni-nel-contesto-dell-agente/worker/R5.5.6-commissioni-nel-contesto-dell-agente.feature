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

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC"
    E che l'exchange applica al conto di "alfa" una commissione dello 0,045% per un ordine a mercato

  Schema dello scenario: Costo di andata e ritorno nel contesto dell'agente
    Dato che "alfa" ha le commissioni nel contesto dell'agente <opzione>
    Quando parte il ciclo di "alfa"
    Allora lo stato del flusso inviato all'agente <esito> il costo di andata e ritorno 0,09%

    Esempi:
      | opzione | esito       |
      | accese  | riporta     |
      | spente  | non riporta |

  Scenario: Commissione non disponibile
    Dato che "alfa" ha le commissioni nel contesto dell'agente accese
    E che l'exchange non risponde alla lettura delle commissioni del conto
    Quando parte il ciclo di "alfa"
    Allora i dati mancanti del ciclo riportano "costo di andata e ritorno"
    E il ciclo di "alfa" si conclude
