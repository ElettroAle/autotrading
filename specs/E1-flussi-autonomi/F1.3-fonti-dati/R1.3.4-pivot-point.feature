# language: it
@R1.3.4 @wip
Funzionalità: R1.3.4 Fonte pivot point
  Come utente
  Voglio che l'agente riceva i pivot point di ogni asset e la posizione del prezzo rispetto a essi
  Perché valuti tendenza, supporti e resistenze vicini

  I pivot si calcolano con la formula classica sulla giornata UTC precedente: PP = (massimo + minimo + chiusura) / 3,
  R1 = 2 × PP − minimo, S1 = 2 × PP − massimo, R2 = PP + (massimo − minimo), S2 = PP − (massimo − minimo).
  All'agente si forniscono i cinque livelli, la posizione del prezzo rispetto al PP (sopra o sotto) e la distanza
  percentuale dal supporto e dalla resistenza più vicini al prezzo corrente.
  Sopra R2 non c'è resistenza più vicina e sotto S2 non c'è supporto più vicino: il contesto lo dichiara.

  Fuori ambito: pivot su altri periodi e altre formule.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC" e la fonte "pivot" attiva
    E che la giornata UTC precedente di "BTC" ha massimo 110, minimo 90 e chiusura 100

  Scenario: Livelli calcolati
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene per "BTC" i livelli:
      | livello | valore |
      | PP      | 100    |
      | R1      | 110    |
      | R2      | 120    |
      | S1      | 90     |
      | S2      | 80     |

  Scenario: Prezzo sopra il pivot
    Dato che il prezzo corrente di "BTC" è 105
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto indica per "BTC" il prezzo sopra il PP
    E il contesto indica per "BTC" la resistenza più vicina R1 a distanza 4,76%
    E il contesto indica per "BTC" il supporto più vicino PP a distanza 4,76%

  Scenario: Prezzo sotto il pivot
    Dato che il prezzo corrente di "BTC" è 95
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto indica per "BTC" il prezzo sotto il PP

  Scenario: Prezzo oltre l'ultima resistenza
    Dato che il prezzo corrente di "BTC" è 125
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto indica per "BTC" nessuna resistenza sopra il prezzo
    E il contesto indica per "BTC" il supporto più vicino R2 a distanza 4%
