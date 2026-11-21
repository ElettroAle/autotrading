# language: it
@R2.4.3
Funzionalità: R2.4.3 Equity curve sovrapposte
  Come utente
  Voglio vedere le equity curve di più flussi sullo stesso grafico
  Perché confronti a colpo d'occhio come si sono comportati nello stesso periodo

  Dalla classifica l'utente sceglie fino a 5 flussi e ne vede le equity curve sovrapposte sullo stesso
  periodo (RF-23.08). Per confrontare flussi con capitali diversi, ogni curva è la variazione percentuale
  rispetto all'equity del suo primo punto nel periodo. Ogni flusso ha un colore distinto e una legenda col
  nome.

  Fuori ambito: il confronto con flussi di altri utenti.

  Contesto:
    Dato che "anna" ha i flussi "alfa" e "beta" con cicli negli ultimi 30 giorni

  Scenario: Curve sovrapposte in percentuale
    Quando "anna" sceglie "alfa" e "beta" nella classifica del periodo "30 giorni" e apre il confronto
    Allora vede le due curve sullo stesso grafico, ciascuna da 0% al primo punto del periodo
    E la legenda mostra "alfa" e "beta" con colori distinti

  Scenario: Al massimo cinque flussi
    Dato che "anna" ha 6 flussi con cicli nel periodo
    Quando "anna" ne ha scelti 5
    Allora non può sceglierne un sesto
