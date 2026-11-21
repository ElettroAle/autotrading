# language: it
@R3.4.3
Funzionalità: R3.4.3 Rendimento corretto dopo incassi e variazioni
  Come utente
  Voglio che il rendimento di un flusso non cambi quando incasso o vario il capitale
  Perché confronto i flussi sui risultati dell'agente, non sui miei movimenti di capitale

  Il rendimento percentuale di un flusso misura solo guadagni e perdite: un aumento, una riduzione o un incasso
  non lo cambiano nel momento in cui avvengono (RF-22.08). Il rendimento è il composto dei rendimenti dei periodi tra
  una variazione di capitale e la successiva: in ogni periodo, valore finale diviso valore iniziale.
  Il PnL del flusso in valuta è la somma di guadagni e perdite e non cambia per una variazione di capitale.
  Lo stesso rendimento vale ovunque compaia: stato e riepilogo del flusso (R2.2.2), classifica (R2.4.2), statistiche
  (R2.2.6), contesto inviato all'agente (RF-13.04).
  L'equity curve (R2.2.3) segna ogni variazione di capitale sul suo istante, con motivo e importo.
  Un flusso senza variazioni ha lo stesso rendimento di oggi.

  Contesto:
    Dato che "anna" ha il flusso "alfa" avviato con capitale allocato 1000 USDC
  Scenario: Il rendimento non cambia con l'incasso
    Dato che il valore di "alfa" è 1100 USDC senza posizioni aperte
    Quando "anna" incassa i profitti di "alfa"
    Allora il rendimento di "alfa" è 10,00%
    E il PnL di "alfa" è 100 USDC
  Scenario: Rendimento composto dopo l'incasso
    Dato che "anna" ha incassato 100 USDC da "alfa" quando valeva 1100 USDC
    Quando il valore di "alfa" passa da 1000 a 1050 USDC
    Allora il rendimento di "alfa" è 15,50%
    E il PnL di "alfa" è 150 USDC
  Scenario: Il rendimento non cambia con un aumento
    Dato che il valore di "alfa" è 1100 USDC
    Quando "anna" aumenta di 900 USDC il capitale allocato di "alfa"
    Allora il rendimento di "alfa" è 10,00%
  Scenario: Rendimento composto dopo un aumento
    Dato che "anna" ha aumentato di 900 USDC il capitale di "alfa" quando valeva 1100 USDC
    Quando il valore di "alfa" passa da 2000 a 2100 USDC
    Allora il rendimento di "alfa" è 15,50%
  Scenario: Il rendimento non cambia con una riduzione
    Dato che il valore di "alfa" è 900 USDC senza posizioni aperte
    Quando "anna" riduce di 300 USDC il capitale allocato di "alfa"
    Allora il rendimento di "alfa" è -10,00%
  Scenario: Flusso senza variazioni
    Quando il valore di "alfa" passa da 1000 a 1080 USDC
    Allora il rendimento di "alfa" è 8,00%
  Scenario: Classifica e contesto dell'agente usano lo stesso rendimento
    Dato che "anna" ha incassato 100 USDC da "alfa" quando valeva 1100 USDC e il valore di "alfa" è ora 1050 USDC
    Quando "anna" apre la classifica dei flussi e parte un ciclo di "alfa"
    Allora la classifica mostra per "alfa" il rendimento 15,50%
    E lo stato del flusso inviato all'agente riporta il rendimento 15,50%
  Scenario: Statistiche dall'inizio con lo stesso rendimento
    Dato che "anna" ha incassato 100 USDC da "alfa" quando valeva 1100 USDC e il valore di "alfa" è ora 1050 USDC
    Quando parte un ciclo di "alfa" e "anna" apre le statistiche di "alfa" dall'inizio
    Allora le statistiche di "alfa" mostrano il rendimento 15,50%
    E il rendimento di "alfa" è 15,50%
  Scenario: Variazione segnata sull'equity curve
    Dato che "anna" ha incassato 100 USDC da "alfa"
    Quando "anna" apre l'equity curve di "alfa"
    Allora la curva segna sull'istante dell'incasso "incasso, 100 USDC"
  Scenario: Il riepilogo del flusso usa lo stesso rendimento
    Dato che "anna" ha incassato 100 USDC da "alfa" quando valeva 1100 USDC e il valore di "alfa" è ora 1050 USDC
    Quando "anna" apre il riepilogo dei suoi flussi
    Allora il riepilogo di "alfa" mostra il rendimento 15,50%
    E lo stato di "alfa" mostra il rendimento 15,50%
