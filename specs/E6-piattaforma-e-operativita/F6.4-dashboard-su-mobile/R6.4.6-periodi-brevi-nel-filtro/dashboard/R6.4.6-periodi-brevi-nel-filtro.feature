# language: it
@R6.4.6
Funzionalità: R6.4.6 Periodi brevi nel filtro
  Come utente
  Voglio scegliere anche periodi brevi, dagli ultimi 30 minuti alle ultime 24 ore
  Perché seguo da vicino cosa fa un flusso nelle ultime ore

  Il menu del periodo offre, in ordine: 30 minuti, 1 ora, 6 ore, 12 ore, 24 ore, 7 giorni, 30 giorni, Dall'inizio,
  Intervallo (R6.4.7). Il predefinito resta Dall'inizio. Un periodo breve vale fino a ora, al minuto (ADR
  periodo-al-minuto), per tutto ciò che il periodo filtra: panoramica, equity curve, statistiche, posizioni chiuse,
  cicli (R6.4.3), classifica (R2.4.2), storico (R2.5.1). Nell'indirizzo il periodo è 30m, 1h, 6h, 12h o 24h. Con pochi
  cicli nel periodo il grafico mostra il solo punto presente o «nessun ciclo nel periodo».
  Aggiorna i testi di R2.2.6 e R2.4.2, che elencano i periodi.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con un ciclo ogni 15 minuti negli ultimi 30 giorni

  Scenario: Periodi del menu
    Quando "anna" apre il menu del periodo nella pagina del flusso "alfa"
    Allora vede in ordine "30 minuti", "1 ora", "6 ore", "12 ore", "24 ore", "7 giorni", "30 giorni", "Dall'inizio", "Intervallo"
    E il periodo scelto è "Dall'inizio"

  Scenario: Ultima ora
    Dato che sono le 10:15
    Quando "anna" sceglie il periodo "1 ora"
    Allora riepilogo, equity curve, statistiche, posizioni chiuse e cicli valgono dalle 9:15 a ora
    E l'indirizzo della pagina porta il periodo "1h"

  Scenario: Classifica su un periodo breve
    Quando "anna" sceglie il periodo "24 ore" nella classifica dei flussi
    Allora il rendimento di ogni flusso è calcolato sulle ultime 24 ore

  Scenario: Grafico con un solo punto
    Dato che il flusso "beta" ha un ciclo ogni 60 minuti e l'ultimo 20 minuti fa
    Quando "anna" sceglie il periodo "30 minuti" nella pagina del flusso "beta"
    Allora l'equity curve mostra il solo punto del ciclo di 20 minuti fa

  Scenario: Nessun ciclo nel periodo
    Dato che l'ultimo ciclo del flusso "beta" è di 45 minuti fa
    Quando "anna" sceglie il periodo "30 minuti" nella pagina del flusso "beta"
    Allora l'equity curve dice "nessun ciclo nel periodo"
    E le statistiche dicono "nessuna operazione nel periodo"
