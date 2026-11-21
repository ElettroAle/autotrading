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
  Scenario: Variazione segnata sull'equity curve
    Dato che "anna" ha incassato 100 USDC da "alfa"
    Quando "anna" apre l'equity curve di "alfa"
    Allora la curva segna sull'istante dell'incasso "incasso, 100 USDC"
