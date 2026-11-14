# language: it
@R2.1.2
Funzionalità: R2.1.2 Aggiornamento dei dati e uso da telefono
  Come utente
  Voglio dati sempre aggiornati e una dashboard usabile anche da telefono
  Perché segua i flussi ovunque io sia

  Mentre una pagina è aperta, i suoi dati si rileggono ogni 30 secondi; un pulsante "Aggiorna" li rilegge
  subito (RF-23.10). La pagina mostra l'istante dell'ultimo aggiornamento. Se l'aggiornamento non riesce,
  restano visibili gli ultimi dati con l'avviso "Dati non aggiornati". Ogni pagina è utilizzabile su schermo
  da computer e da telefono.

  Fuori ambito: aggiornamenti spinti dal server in tempo reale.

  Contesto:
    Dato che "anna" ha aperto la pagina del flusso "alfa" alle 10:00:00

  Scenario: Aggiornamento automatico
    Quando un nuovo ciclo del flusso "alfa" si conclude alle 10:00:10
    Allora alle 10:00:30 la pagina mostra il nuovo ciclo
    E l'istante dell'ultimo aggiornamento è 10:00:30

  Scenario: Aggiornamento su richiesta
    Quando un nuovo ciclo del flusso "alfa" si conclude alle 10:00:10
    E "anna" preme "Aggiorna" alle 10:00:12
    Allora la pagina mostra il nuovo ciclo
    E l'istante dell'ultimo aggiornamento è 10:00:12

  Scenario: Aggiornamento non riuscito
    Dato che l'interfaccia programmatica non risponde
    Quando arriva il momento dell'aggiornamento
    Allora la pagina mostra ancora i dati delle 10:00:00
    E mostra l'avviso "Dati non aggiornati"

  Scenario: Uso da telefono
    Quando "anna" apre la pagina del flusso "alfa" su uno schermo largo 390 pixel
    Allora tutti i contenuti sono leggibili senza scorrimento orizzontale
