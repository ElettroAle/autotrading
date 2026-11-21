# language: it
@R6.4.8
Funzionalità: R6.4.8 Prossima esecuzione nella panoramica
  Come utente
  Voglio vedere nella panoramica del flusso quando partirà il prossimo ciclo
  Perché so quando il flusso tornerà a decidere senza aprire l'elenco dei flussi

  La panoramica della pagina del flusso mostra «Prossima esecuzione prevista» con data e ora, come la scheda del flusso
  nell'elenco (R2.2.2): lo stesso istante, calcolato dalla pianificazione del flusso (R1.2.1). Vale solo per un flusso
  attivo; per un flusso fermo, in pausa o archiviato il valore non compare. Non dipende dal periodo scelto.
  Nella stessa panoramica «Guadagno totale» si chiama «Guadagno attuale» (Bug 612).

  Contesto:
    Dato che "anna" ha il flusso "alfa" con un ciclo ogni 15 minuti

  Scenario: Flusso archiviato
    Dato che il flusso "alfa" è archiviato
    Quando "anna" legge il flusso "alfa"
    Allora il flusso letto è nello stato "archiviato"
