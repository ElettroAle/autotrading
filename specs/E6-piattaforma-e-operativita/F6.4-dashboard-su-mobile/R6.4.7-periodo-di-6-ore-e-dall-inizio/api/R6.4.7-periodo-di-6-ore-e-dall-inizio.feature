# language: it
@R6.4.7
Funzionalità: R6.4.7 Periodo di 6 ore e «Dall'inizio»
  Come utente
  Voglio il periodo delle ultime 6 ore e un nome chiaro per il periodo che parte dall'inizio del flusso
  Perché le 6 ore stanno tra l'ora e la mezza giornata che seguo più spesso, e «Tutta la vita» non dice da quando

  Il menu del periodo offre, in ordine: 30 minuti, 1 ora, 6 ore, 12 ore, 24 ore, 7 giorni, 30 giorni,
  Dall'inizio, Intervallo. Il predefinito è Dall'inizio, che sostituisce «Tutta la vita» con lo stesso significato.
  Le 6 ore valgono fino a ora, al minuto, per tutto ciò che il periodo filtra, come gli altri periodi brevi (R6.4.6).
  Nell'indirizzo il periodo è 6h; un indirizzo già salvato con il periodo dall'inizio continua ad aprirsi.
  Aggiorna i testi di R6.4.6, R2.2.6 e R2.4.2, che elencano i periodi.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con un ciclo ogni 15 minuti negli ultimi 30 giorni

  Scenario: Periodi del menu
    Quando "anna" apre il menu del periodo nella pagina del flusso "alfa"
    Allora vede in ordine "30 minuti", "1 ora", "6 ore", "12 ore", "24 ore", "7 giorni", "30 giorni", "Dall'inizio", "Intervallo"
    E il periodo scelto è "Dall'inizio"

  Scenario: Ultime 6 ore
    Dato che sono le 10:15
    Quando "anna" sceglie il periodo "6 ore"
    Allora riepilogo, equity curve, statistiche, posizioni chiuse e cicli valgono dalle 4:15 a ora
    E l'indirizzo della pagina porta il periodo "6h"

  Scenario: Classifica sulle ultime 6 ore
    Quando "anna" sceglie il periodo "6 ore" nella classifica dei flussi
    Allora il rendimento di ogni flusso è calcolato sulle ultime 6 ore
