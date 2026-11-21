# language: it
@R2.4.2
Funzionalità: R2.4.2 Classifica dei flussi
  Come utente
  Voglio una classifica dei miei flussi
  Perché scelga le strategie migliori

  La classifica confronta i flussi dell'utente (RF-01.06) su: rendimento in percentuale, PnL, commissioni,
  win rate, numero di operazioni, drawdown massimo e costo del modello IA (RF-03.06). Il periodo è a scelta:
  30 minuti, 1 ora, 6 ore, 12 ore, 24 ore, 7 giorni, 30 giorni, dall'inizio del flusso (predefinito) o un intervallo
  libero (R6.4.6, R6.4.7). Il rendimento del periodo si calcola sull'equity curve (R2.2.3) tra il primo e l'ultimo punto
  del periodo; il drawdown massimo è la più grande discesa percentuale dell'equity da un massimo precedente, nel
  periodo. PnL, commissioni, win rate e operazioni seguono le statistiche (R2.2.6). L'utente ordina la classifica
  per qualsiasi colonna; il predefinito è il rendimento decrescente. Compaiono i flussi non archiviati con almeno
  un ciclo nel periodo. Disponibile dalla dashboard e dall'interfaccia programmatica.

  Fuori ambito: i flussi di altri utenti, i flussi archiviati, le bozze.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con equity per ciclo 300, 330, 297, 360 USDC
    E che "anna" ha il flusso "beta" con equity per ciclo 200, 210 USDC
    E che "bruno" ha il flusso "omega"

  Scenario: Classifica sull'intera vita
    Quando "anna" apre la classifica
    Allora "alfa" è primo con rendimento +20,00% e drawdown massimo 10,00%
    E "beta" è secondo con rendimento +5,00% e drawdown massimo 0,00%
    E la classifica non contiene "omega"

  Scenario: Ordinamento per un'altra colonna
    Quando "anna" ordina la classifica per drawdown massimo crescente
    Allora "beta" è primo

  Scenario: Classifica su un periodo
    Dato che negli ultimi 7 giorni "alfa" ha equity 297 e 360 USDC
    Quando "anna" sceglie il periodo "7 giorni"
    Allora "alfa" mostra rendimento +21,21% e drawdown massimo 0,00%

  Scenario: Flusso senza cicli nel periodo
    Dato che il flusso "gamma" non ha cicli negli ultimi 7 giorni
    Quando "anna" sceglie il periodo "7 giorni"
    Allora la classifica non contiene "gamma"

  Scenario: PnL, commissioni, win rate, operazioni e costo del modello nella classifica
    Dato che "beta" ha chiuso posizioni con PnL netto +8 e -2 USDC, commissioni totali 1 USDC e costo del modello 0,40 USD
    Quando "anna" apre la classifica
    Allora la riga di "beta" nella classifica mostra:
      | colonna              | valore   |
      | PnL                  | +6 USDC  |
      | Commissioni          | 1 USDC   |
      | Win rate             | 50,00%   |
      | Operazioni           | 2        |
      | Costo del modello IA | 0,40 USD |

  Schema dello scenario: Bozze e flussi archiviati fuori dalla classifica
    Dato che "anna" ha il flusso "gamma" <stato> con equity per ciclo 100, 500 USDC
    Quando "anna" apre la classifica
    Allora la classifica non contiene "gamma"

    Esempi:
      | stato      |
      | archiviato |
      | in bozza   |
