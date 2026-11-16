# language: it
@R6.4.3
Funzionalità: R6.4.3 Pagina del flusso a schede con periodo comune
  Come utente
  Voglio una pagina del flusso con un solo periodo che vale per tutto ciò che vedo
  Perché nessun filtro agisce di nascosto su una parte che non sto guardando

  La pagina del flusso ha, in quest'ordine: nome, stato con i comandi di stato (Avvia, Pausa, Riprendi, Stop) e
  avviso della rete; il periodo; le schede Panoramica, Posizioni chiuse e Cicli; il contenuto della scheda scelta.
  Il periodo sta sopra le schede e vale per tutte: Panoramica (riepilogo R6.4.2, equity curve, statistiche,
  posizioni aperte attuali), Posizioni chiuse e Cicli. Le posizioni aperte sono quelle attuali e lo dicono. Il
  periodo si sceglie dal menu (R2.2.8) oppure trascinando sull'equity curve da un istante a un altro, anche col
  dito; un intervallo scelto così compare come etichetta "dal … al …" con il comando per toglierlo. Periodo,
  intervallo e scheda stanno nell'indirizzo della pagina: ricaricare o tornare indietro li conserva. Ogni ciclo
  fallito compare sull'equity curve come un segno rosso riconoscibile, che porta al dettaglio del ciclo; i cicli
  conclusi non hanno segni. L'elenco dei cicli recenti nella pagina è tolto. Configurazione, versioni, modifica,
  duplica ed esporta stanno fuori dalle schede, nel comando Configurazione, perché non dipendono dal periodo.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con cicli e posizioni chiuse negli ultimi 30 giorni

  Scenario: Il periodo vale per tutte le schede
    Quando "anna" sceglie il periodo "ultima settimana" nella pagina del flusso "alfa"
    E apre la scheda Cicli
    Allora vede solo i cicli dell'ultima settimana e il periodo resta "ultima settimana"

  Scenario: Intervallo trascinando sul grafico
    Quando "anna" trascina sull'equity curve dal 10 al 12 novembre 2026
    Allora riepilogo, grafico e statistiche valgono dal 10 al 12 novembre 2026
    E compare l'etichetta "dal 10/11/2026 al 12/11/2026" con il comando per toglierla

  Scenario: Togliere l'intervallo
    Dato che "anna" ha scelto l'intervallo dal 10 al 12 novembre 2026
    Quando toglie l'etichetta dell'intervallo
    Allora la pagina torna al periodo del menu

  Scenario: Periodo e scheda nell'indirizzo
    Dato che "anna" è sulla scheda Posizioni chiuse con l'intervallo dal 10 al 12 novembre 2026
    Quando ricarica la pagina
    Allora vede ancora la scheda Posizioni chiuse con lo stesso intervallo

  Scenario: Ciclo fallito sul grafico
    Dato che il ciclo del 11/11/2026 alle 10:15 del flusso "alfa" è fallito
    Quando "anna" sceglie il suo segno sull'equity curve
    Allora vede il dettaglio di quel ciclo

  Scenario: Niente cicli recenti nella pagina
    Quando "anna" apre la pagina del flusso "alfa"
    Allora la pagina non mostra l'elenco dei cicli recenti

  Scenario: Configurazione fuori dalle schede
    Quando "anna" sceglie Configurazione nella pagina del flusso "alfa"
    Allora vede configurazione, versioni e i comandi Modifica, Duplica ed Esporta, senza il periodo

  Scenario: Posizioni aperte attuali
    Quando "anna" apre la Panoramica del flusso "alfa" con il periodo "ultima settimana"
    Allora le posizioni aperte sono quelle attuali e la pagina lo dice
