# language: it
@R6.4.5
Funzionalità: R6.4.5 Schede riconoscibili
  Come utente
  Voglio riconoscere a colpo d'occhio un gruppo di schede
  Perché capisco che sto cambiando vista nella stessa pagina e non aprendo un collegamento

  In tutta la dashboard le schede (elenco e classifica dei flussi, storico, pagina del flusso) usano un solo
  componente con aspetto da schede, sobrio e coerente con il resto: le schede stanno su una barra comune, quella
  scelta ha sfondo e testo evidenziati e un indicatore, le altre hanno l'aspetto di comandi non scelti. Le schede
  hanno il ruolo accessibile di schede e si scelgono anche da tastiera; su schermi stretti la barra resta su una
  riga e scorre al proprio interno.

  Scenario: Scheda scelta evidente
    Quando "anna" apre l'elenco dei flussi
    Allora la scheda "Elenco" è evidenziata come scelta e "Classifica" ha l'aspetto di una scheda non scelta

  Scenario: Ruolo di schede
    Quando "anna" apre lo storico
    Allora le viste Cicli, Posizioni chiuse e Ordini sono schede di un gruppo di schede

  Scenario: Schede su schermo stretto
    Dato uno schermo largo 360 pixel
    Quando "anna" apre la pagina del flusso
    Allora la barra delle schede sta su una riga e la pagina non scorre in orizzontale

  Scenario: Schede selezionabili da tastiera
    Quando "anna" apre lo storico
    E sceglie con la freccia a destra la scheda dopo "Cicli"
    Allora la scheda "Posizioni chiuse" è scelta e ha il fuoco
