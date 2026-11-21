# language: it
@R6.5.6
Funzionalità: R6.5.6 Legenda dell'equity curve del flusso
  Come utente
  Voglio sotto l'equity curve del flusso la legenda dei segni che il grafico disegna
  Perché capisca che cosa significano punti, linee e simboli senza doverlo indovinare

  Sotto l'equity curve della pagina del flusso c'è la legenda. Ogni voce mostra lo stesso segno del grafico accanto al
  suo nome, così non si legge solo dal colore: punto verde "sopra il capitale iniziale", punto rosso "sotto il capitale
  iniziale", linea tratteggiata "capitale iniziale", croce rossa "ciclo fallito", rombo viola "variazione di capitale".
  Punti e capitale iniziale ci sono sempre; croce e rombo solo se il periodo mostrato ha almeno un ciclo fallito o una
  variazione di capitale. Su telefono le voci vanno a capo su più righe, senza scorrimento orizzontale; su desktop
  stanno su una riga se c'è spazio. La legenda del confronto delle equity curve usa lo stesso componente condiviso.

  Fuori ambito: nascondere o evidenziare una serie toccando la sua voce.

  Contesto:
    Dato che "anna" ha il flusso attivo "alfa" con cicli nel periodo mostrato

  Scenario: Legenda dei punti e del capitale iniziale
    Quando "anna" apre la pagina del flusso "alfa"
    Allora sotto l'equity curve la legenda mostra "sopra il capitale iniziale", "sotto il capitale iniziale" e "capitale iniziale", ciascuna col suo segno
    E la legenda non mostra "ciclo fallito" né "variazione di capitale"

  Scenario: Legenda degli eventi presenti nel periodo
    Dato che "alfa" ha un ciclo fallito e una variazione di capitale nel periodo mostrato
    Quando "anna" apre la pagina del flusso "alfa"
    Allora la legenda mostra anche "ciclo fallito" con la croce rossa e "variazione di capitale" col rombo viola

  Scenario: Legenda leggibile su telefono
    Dato che "alfa" ha un ciclo fallito e una variazione di capitale nel periodo mostrato
    Quando "anna" apre la pagina del flusso "alfa" su un telefono
    Allora tutte le voci della legenda sono visibili senza scorrimento orizzontale

  Scenario: Legenda del confronto delle equity curve
    Dato che "anna" ha anche il flusso attivo "beta" con cicli nel periodo mostrato
    Quando "anna" sceglie "alfa" e "beta" nella classifica del periodo "30 giorni" e apre il confronto
    Allora sotto il grafico del confronto la legenda condivisa mostra "alfa" e "beta", ciascuno col segno della sua curva
