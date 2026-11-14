# language: it
@R2.2.6
Funzionalità: R2.2.6 Statistiche del flusso
  Come utente
  Voglio vedere le statistiche di un flusso
  Perché valuti la qualità della strategia oltre al rendimento

  Per il periodo scelto (tutta la vita predefinita, 7 giorni, 30 giorni, intervallo libero) la dashboard
  mostra: operazioni vinte e perse, win rate, PnL medio delle vincenti e delle perdenti, commissioni totali,
  numero di operazioni, costo del modello IA (RF-23.05). Un'operazione è una posizione chiusa nel periodo:
  vinta con PnL netto positivo, persa con PnL netto negativo; con PnL netto nullo non è né vinta né persa,
  conta nel numero di operazioni ma non nel win rate, che è vinte su vinte più perse. Disponibile dalla
  dashboard e dall'interfaccia programmatica.

  Fuori ambito: il drawdown, che sta nella classifica (R2.4.2).

  Contesto:
    Dato che il flusso "alfa" ha chiuso 4 posizioni con PnL netto +20, +10, -6 e -4 USDC e commissioni totali 3 USDC
    E che le chiamate al modello del flusso sono costate 1,20 USD

  Scenario: Statistiche sull'intera vita
    Quando "anna" apre le statistiche del flusso "alfa"
    Allora vede 2 vinte, 2 perse, win rate 50,00%, PnL medio vincenti +15 USDC, PnL medio perdenti -5 USDC, commissioni 3 USDC, 4 operazioni, costo del modello 1,20 USD

  Scenario: Statistiche su un periodo
    Dato che solo le posizioni con PnL +20 e -4 USDC sono state chiuse negli ultimi 7 giorni
    Quando "anna" sceglie il periodo "7 giorni"
    Allora vede 1 vinta, 1 persa e 2 operazioni

  Scenario: Operazione in pareggio
    Dato che il flusso "alfa" chiude una quinta posizione con PnL netto 0 USDC
    Quando "anna" apre le statistiche del flusso "alfa"
    Allora vede 2 vinte, 2 perse, win rate 50,00% e 5 operazioni

  Scenario: Nessuna operazione nel periodo
    Dato che il flusso "beta" non ha posizioni chiuse
    Quando "anna" apre le statistiche del flusso "beta"
    Allora vede 0 operazioni e win rate "non disponibile"
