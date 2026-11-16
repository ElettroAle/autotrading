# language: it
@R3.3.2
Funzionalità: R3.3.2 Stato della riconciliazione nella dashboard
  Come utente
  Voglio vedere nella dashboard se ogni conto torna con l'exchange e confermare un allarme
  Perché capisco che cosa non torna e sblocco i flussi senza usare l'interfaccia programmatica

  Nella pagina dei conti ogni conto mostra lo stato della riconciliazione (RF-23.09): "allineato" oppure
  "allarme", con data e ora dell'ultimo confronto, saldo atteso, saldo letto, scostamento e soglia del conto (R3.3.1).
  Con un allarme aperto la pagina offre il comando "Ho verificato", che chiede conferma e chiude l'allarme.
  Il conto mostra l'elenco dei suoi allarmi, dal più recente, aperti e chiusi, con data e ora di apertura e di
  conferma.
  La soglia di scostamento si modifica dalla pagina del conto.
  Ogni flusso di un conto con un allarme aperto mostra "aperture sospese: allarme di riconciliazione sul conto".

  Contesto:
    Dato che "anna" ha il conto "test-1" con il flusso "alfa" e soglia di scostamento 1%

  Scenario: Conto allineato
    Dato che l'ultimo confronto del conto "test-1" ha saldo atteso 1000 USDC e saldo letto 1000 USDC
    Quando "anna" apre la pagina dei conti
    Allora il conto "test-1" mostra lo stato "allineato" con data e ora dell'ultimo confronto

  Scenario: Conto in allarme
    Dato che sul conto "test-1" c'è un allarme di riconciliazione con saldo atteso 1000 USDC e saldo letto 980 USDC
    Quando "anna" apre la pagina dei conti
    Allora il conto "test-1" mostra lo stato "allarme" con saldo atteso 1000 USDC, saldo letto 980 USDC, scostamento 2% e soglia 1%
    E il conto "test-1" offre il comando "Ho verificato"

  Scenario: Conferma dalla dashboard
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    Quando "anna" sceglie "Ho verificato" sul conto "test-1" e conferma
    Allora il conto "test-1" mostra lo stato "allineato"

  Scenario: Conferma annullata
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    Quando "anna" sceglie "Ho verificato" sul conto "test-1" e annulla
    Allora il conto "test-1" mostra lo stato "allarme"

  Scenario: Elenco degli allarmi del conto
    Dato che il conto "test-1" ha un allarme chiuso ieri e un allarme aperto oggi
    Quando "anna" apre gli allarmi del conto "test-1"
    Allora l'elenco mostra prima l'allarme di oggi, aperto, poi quello di ieri con data e ora della conferma

  Scenario: Soglia modificata dalla pagina del conto
    Quando "anna" imposta dalla pagina del conto "test-1" la soglia di scostamento a 3%
    Allora il conto "test-1" mostra la soglia 3%

  Scenario: Avviso sul flusso
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    Quando "anna" apre il flusso "alfa" nella dashboard
    Allora la pagina mostra "aperture sospese: allarme di riconciliazione sul conto test-1"
