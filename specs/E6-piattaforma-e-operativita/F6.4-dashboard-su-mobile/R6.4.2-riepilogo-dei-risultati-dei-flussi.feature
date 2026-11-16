# language: it
@R6.4.2
Funzionalità: R6.4.2 Riepilogo dei risultati dei flussi
  Come utente
  Voglio vedere subito come sta andando ogni flusso
  Perché capisco in un colpo d'occhio guadagno, esposizione ed errori senza leggere tabelle

  In cima alla pagina del flusso e in ogni scheda dell'elenco dei flussi un riepilogo mostra: guadagno totale e
  guadagno nel periodo scelto, ciascuno come importo nella valuta di regolamento del conto e come percentuale sul
  capitale iniziale, verde se positivo e rosso se negativo; numero di posizioni aperte, che porta alle posizioni
  aperte del flusso; numero di cicli falliti nel periodo, evidenziato solo se maggiore di zero, che porta ai cicli
  del flusso filtrati sui falliti. Nell'elenco il periodo è quello scelto in cima all'elenco (R2.2.8). La fila
  degli esiti dei cicli recenti nelle schede dell'elenco è tolta: il riepilogo la sostituisce. Le schede
  dell'elenco mostrano in secondo piano conto, modello, versione, ultima e prossima esecuzione; la voce Ambiente è
  tolta perché l'installazione è già indicata in alto.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con capitale iniziale 100 USDC

  Scenario: Riepilogo nella pagina del flusso
    Dato che il flusso "alfa" ha guadagnato 2,5 USDC in tutto e 0,4 USDC nell'ultima settimana
    E ha 1 posizione aperta e 2 cicli falliti nell'ultima settimana
    Quando "anna" apre la pagina del flusso "alfa" con il periodo "ultima settimana"
    Allora il riepilogo mostra guadagno totale "+2,50 USDC · +2,50%" e nel periodo "+0,40 USDC · +0,40%"
    E mostra 1 posizione aperta e 2 cicli falliti

  Scenario: Perdita in rosso
    Dato che il flusso "alfa" ha perso 1,2 USDC in tutto
    Quando "anna" apre la pagina del flusso "alfa"
    Allora il guadagno totale "-1,20 USDC · -1,20%" è in rosso

  Scenario: Nessun errore nel periodo
    Dato che il flusso "alfa" non ha cicli falliti nel periodo
    Quando "anna" apre la pagina del flusso "alfa"
    Allora il riepilogo dice "nessun errore" senza evidenza

  Scenario: Dai cicli falliti ai cicli filtrati
    Dato che il flusso "alfa" ha 2 cicli falliti nel periodo
    Quando "anna" sceglie i cicli falliti nel riepilogo
    Allora vede i cicli del flusso "alfa" filtrati sui falliti

  Scenario: Dalle posizioni aperte alla loro vista
    Dato che il flusso "alfa" ha 1 posizione aperta
    Quando "anna" sceglie le posizioni aperte nel riepilogo
    Allora vede le posizioni aperte del flusso "alfa"

  Scenario: Riepilogo nelle schede dell'elenco
    Dato che il flusso "alfa" ha guadagnato 2,5 USDC in tutto
    Quando "anna" apre l'elenco dei flussi
    Allora la scheda di "alfa" mostra il riepilogo e non mostra la fila degli esiti dei cicli né la voce Ambiente

  Scenario: Valuta del conto
    Dato che il conto del flusso "alfa" regola in "USDT"
    Quando "anna" apre la pagina del flusso "alfa"
    Allora gli importi del riepilogo sono in "USDT"
