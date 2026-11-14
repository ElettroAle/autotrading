# language: it
@R2.3.4
Funzionalità: R2.3.4 Comandi dei flussi dalla dashboard
  Come utente
  Voglio avviare, mettere in pausa, riprendere, fermare e archiviare un flusso dalla dashboard
  Perché governi i flussi con un clic

  Dalla dashboard l'utente esegue i comandi di un flusso: avvio, pausa, ripresa, stop e archiviazione, con le
  regole dell'interfaccia programmatica (R1.1.4, R1.1.5, R1.1.6). Lo stop e l'archiviazione chiedono una
  conferma che dice che cosa accadrà alle posizioni aperte. La dashboard offre solo i comandi ammessi nello
  stato del flusso. L'avvio di un flusso su un exchange configurato sulla rete reale chiede una conferma che avvisa
  che il flusso opererà con denaro reale.

  Fuori ambito: la chiusura di emergenza (F3).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con una posizione aperta su "BTC"

  Scenario: Pausa e ripresa
    Quando "anna" mette in pausa il flusso "alfa"
    E "anna" riprende il flusso "alfa"
    Allora il flusso "alfa" è nello stato "attivo"

  Scenario: Stop con conferma
    Quando "anna" chiede lo stop del flusso "alfa"
    Allora la conferma dice che la posizione su "BTC" sarà chiusa
    E dopo la conferma il flusso "alfa" è nello stato "fermo"

  Scenario: Solo i comandi ammessi
    Quando "anna" apre il flusso "alfa"
    Allora vede i comandi "pausa" e "stop"
    E non vede il comando "avvia"

  Scenario: Comando rifiutato
    Dato che il flusso "gamma" è fermo e il suo conto non ha capitale libero sufficiente
    Quando "anna" avvia il flusso "gamma"
    Allora la dashboard mostra il motivo del rifiuto

  Scenario: Avvio su rete reale con avviso
    Dato che il flusso "delta" è assegnato a un conto su un exchange configurato sulla rete reale
    Quando "anna" avvia il flusso "delta"
    Allora la conferma avvisa che il flusso opererà con denaro reale
    E dopo la conferma il flusso "delta" è nello stato "attivo"

  Scenario: Avvio su rete di test senza avviso
    Dato che il flusso "epsilon" è assegnato a un conto su un exchange configurato sulla rete di test
    Quando "anna" avvia il flusso "epsilon"
    Allora il flusso "epsilon" è nello stato "attivo" senza conferma
