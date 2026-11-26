# language: it
@R5.5.7
Funzionalità: R5.5.7 Informazioni su ogni campo di configurazione
  Come utente
  Voglio accanto a ogni campo di configurazione un pulsante info che mi dica che cosa fa quel campo
  Perché non debba conoscere la piattaforma per sapere che cosa fa un campo

  Il modulo di creazione e modifica di un flusso ha molte impostazioni e nessuna spiegazione accanto: per sapere che cosa
  fa un campo bisogna conoscere la piattaforma.

  Regole.
  - Ogni campo del modulo di creazione e modifica del flusso, e ogni impostazione della pagina del conto, ha accanto
    all'etichetta un pulsante info. Vale per i campi di oggi e per ogni campo aggiunto dopo: un campo senza testo info
    non è ammesso.
  - Campi di oggi del flusso: nome, conto, asset, intervallo di ciclo, modello, ogni parametro del modello, ogni fonte,
    ogni adapter con il suo peso, ogni parametro di un adapter, istruzioni, system prompt, capitale allocato, leva
    massima, esposizione massima sul margine, esposizione massima sul valore, esposizione complessiva sul margine,
    esposizione complessiva sul valore, porta al minimo, fallimenti consecutivi massimi, perdita giornaliera massima,
    perdita massima dal picco, ripresa delle aperture, stop loss predefinito, take profit predefinito, confidenza minima,
    memoria attiva, decisioni della memoria, giorni della memoria, lunghezza del testo della memoria, tutte le decisioni.
  - Il testo dice, in italiano e in questo ordine: che cosa fa il campo, i valori ammessi, il valore predefinito o che
    cosa succede lasciandolo vuoto.
  - Il testo di un parametro di un adapter di una fonte e di un parametro di un modello è la descrizione che
    quell'adapter o quel modello dichiara: ogni parametro ne ha una, non vuota.
  - Il pulsante si attiva con clic, tocco o tastiera (Invio o Spazio quando ha il fuoco); il testo si chiude con Esc,
    con un clic fuori o attivando di nuovo il pulsante. Un solo testo aperto alla volta. Il nome accessibile del
    pulsante è «Informazioni su <etichetta del campo>».
  - Il componente è uno solo, condiviso, usato da ogni modulo della dashboard.

  Fuori ambito: descrizioni negli strumenti MCP, guida in linea, traduzioni.

  Contesto:
    Dato che "anna" ha aperto il modulo di modifica del flusso "alfa"

  Schema dello scenario: Testo info di un campo
    Quando "anna" attiva il pulsante "Informazioni su <campo>"
    Allora vede il testo "<testo>"

    Esempi:
      | campo                        | testo                                                                                                                                                         |
      | Stop loss predefinito        | Distanza dello stop loss dal prezzo d'ingresso, in percentuale, per ogni apertura in cui l'agente non indica uno stop. Da 0,1 a 50. Predefinito: 5.             |
      | Take profit predefinito      | Distanza dell'obiettivo dal prezzo d'ingresso, in percentuale, per ogni apertura in cui l'agente non indica un obiettivo. Maggiore di 0. Vuoto: nessun take profit. |
      | Perdita giornaliera massima  | Perdita del giorno, in percentuale dei soldi del flusso, oltre la quale le aperture si sospendono. Da 0,1 a 100. Vuoto: nessun limite.                         |
      | Confidenza minima            | Confidenza, da 0 a 100, sotto la quale un'apertura decisa dall'agente non viene eseguita. Vuoto: ogni apertura passa.                                            |

  Scenario: Ogni campo del modulo ha il suo pulsante info
    Allora ogni campo del modulo ha accanto all'etichetta un pulsante "Informazioni su" seguito dall'etichetta del campo
    E attivando ciascun pulsante compare un testo non vuoto

  Scenario: Parametro di un adapter
    Dato che il flusso "alfa" ha la fonte indicatori con l'adapter "Hyperliquid"
    Quando "anna" attiva il pulsante "Informazioni su rsi_periodi"
    Allora vede la descrizione che l'adapter "Hyperliquid" dichiara per il parametro rsi_periodi

  Scenario: Parametro del modello
    Quando "anna" attiva il pulsante "Informazioni su temperature"
    Allora vede la descrizione che il modello di "alfa" dichiara per il parametro temperature

  Schema dello scenario: Il testo si chiude
    Dato che "anna" ha aperto il testo info di "Stop loss predefinito"
    Quando "anna" <azione>
    Allora il testo info di "Stop loss predefinito" non è più visibile

    Esempi:
      | azione                                  |
      | preme Esc                               |
      | fa clic fuori dal testo                 |
      | attiva di nuovo lo stesso pulsante info |

  Scenario: Un solo testo aperto alla volta
    Dato che "anna" ha aperto il testo info di "Stop loss predefinito"
    Quando "anna" attiva il pulsante "Informazioni su Confidenza minima"
    Allora vede il testo info di "Confidenza minima"
    E il testo info di "Stop loss predefinito" non è più visibile

  Schema dello scenario: Pulsante usato dalla tastiera
    Dato che il pulsante "Informazioni su Stop loss predefinito" ha il fuoco
    Quando "anna" preme <tasto>
    Allora vede il testo info di "Stop loss predefinito"

    Esempi:
      | tasto |
      | Invio |
      | Spazio |

  Scenario: Modulo di creazione
    Dato che "anna" ha aperto il modulo di creazione di un flusso
    Allora ogni campo del modulo ha accanto all'etichetta un pulsante "Informazioni su" seguito dall'etichetta del campo

  Scenario: Pagina del conto
    Dato che "anna" ha aperto la pagina del conto "principale"
    Allora ogni impostazione del conto ha accanto all'etichetta un pulsante "Informazioni su" seguito dall'etichetta dell'impostazione
