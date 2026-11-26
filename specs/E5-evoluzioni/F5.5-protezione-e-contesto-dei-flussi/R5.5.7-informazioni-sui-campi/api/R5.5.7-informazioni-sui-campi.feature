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

  Scenario: Ogni parametro di adapter ha una descrizione
    Quando "anna" legge l'elenco delle fonti con i loro adapter
    Allora ogni parametro di ogni adapter riporta una descrizione non vuota

  Scenario: Ogni parametro di modello ha una descrizione
    Quando "anna" legge l'elenco dei modelli con i loro parametri
    Allora ogni parametro di ogni modello riporta una descrizione non vuota
