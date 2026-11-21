# language: it
@R3.3.1
Funzionalità: R3.3.1 Allarme sul saldo non spiegato
  Come utente
  Voglio un allarme che blocca le nuove aperture quando il saldo di un conto non torna
  Perché un intervento manuale, una liquidazione o un errore non lasciano i flussi a operare su numeri falsi

  A ogni ciclo, per il conto del flusso, la piattaforma confronta il saldo letto dall'exchange con il saldo atteso:
  l'ultimo saldo di riferimento più ciò che lo spiega, cioè esecuzioni, commissioni e funding dei flussi, e depositi e
  prelievi che l'exchange dichiara (R1.6.1). Ogni esecuzione e pagamento di funding dei flussi conta una sola volta:
  quello pubblicato dall'exchange dopo una lettura del saldo, con un istante non successivo a quella lettura, era già
  compreso nel saldo letto allora (Bug 506). Conta invece ogni esecuzione e pagamento di funding dei flussi successivo
  alla lettura precedente, chiunque lo abbia registrato: anche le chiusure di un'inversione o di un incasso dei profitti,
  registrate prima della riconciliazione (Bug 633).
  Ogni conto ha una soglia di scostamento, in percentuale del saldo atteso, da 0,1 a 100, pari a 1 se non indicata.
  Uno scostamento oltre la soglia apre un allarme di riconciliazione sul conto (RF-13.07): si registrano saldo atteso,
  saldo letto e scostamento, l'utente viene avvisato, e le aperture di tutti i flussi del conto sono sospese finché
  l'utente non conferma di aver verificato. Chiusure e aggiornamenti del piano di uscita si eseguono; i cicli
  continuano.
  Uno scostamento entro la soglia si registra come variazione del saldo non spiegata (R1.6.2), senza allarme e senza
  notifica.
  Un deposito o un prelievo dichiarato dall'exchange è spiegato: non apre l'allarme e non è una variazione non
  spiegata.
  Con un allarme aperto non se ne apre un secondo sullo stesso conto.
  La conferma dell'utente chiude l'allarme, prende il saldo letto come nuovo riferimento, fa riprendere le aperture
  e si registra con data e ora.
  Fuori ambito: le posizioni non attribuibili, che restano solo segnalate (R1.6.2); lo stato nella dashboard (R3.3.2).

  Contesto:
    Dato che "anna" ha il conto "test-1" con i flussi attivi "alfa" e "beta" e soglia di scostamento 1%
    E che "anna" ha il conto "test-2" con il flusso attivo "gamma"
    E che il saldo atteso del conto "test-1" è 1000 USDC

  Scenario: Conferma dell'utente
    Dato che sul conto "test-1" c'è un allarme di riconciliazione con saldo letto 980 USDC
    Quando "anna" conferma di aver verificato il conto "test-1"
    Allora l'allarme del conto "test-1" è chiuso
    E il saldo atteso del conto "test-1" è 980 USDC
    E le aperture di "alfa" e "beta" non sono sospese

  Scenario: Conferma senza allarme
    Quando "anna" conferma di aver verificato il conto "test-1"
    Allora il comando viene rifiutato con "il conto test-1 non ha un allarme di riconciliazione aperto"

  Schema dello scenario: Soglia fuori dall'intervallo
    Quando "anna" imposta la soglia di scostamento del conto "test-1" a <valore>%
    Allora la modifica viene rifiutata con "la soglia di scostamento va da 0,1 a 100"

    Esempi:
      | valore |
      | 0      |
      | 101    |

  Scenario: La conferma si registra con data e ora
    Dato che sul conto "test-1" c'è un allarme di riconciliazione
    E che sono le 11:00 UTC del 12 novembre 2026
    Quando "anna" conferma di aver verificato il conto "test-1"
    Allora la conferma dell'allarme del conto "test-1" è registrata alle 11:00 UTC del 12 novembre 2026
