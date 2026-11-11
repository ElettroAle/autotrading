# language: it
@R1.4.5 @wip
Funzionalità: R1.4.5 Risposta dell'agente non conforme
  Come utente
  Voglio che una risposta dell'agente non conforme non produca mai ordini
  Perché un errore del modello non diventi un'operazione sul conto

  Una decisione è non conforme se manca un campo obbligatorio, se un valore è fuori dal tipo o dall'intervallo
  ammesso, se l'azione non è tra quelle ammesse o se l'asset non è del flusso.
  Le decisioni non conformi si scartano e si registrano con il motivo; le decisioni conformi dello stesso ciclo
  proseguono verso il controllo del rischio. Un asset senza decisione è trattato come "mantieni" e registrato
  come decisione mancante.
  Una risposta non leggibile per intero scarta tutte le decisioni: il ciclo si registra con la risposta
  integrale e nessun ordine.

  Fuori ambito: nuovi tentativi verso il modello nello stesso ciclo.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con asset "BTC, ETH, SOL"

  Scenario: Solo le decisioni non conformi sono scartate
    Dato che l'agente risponde apri long su "BTC" con quota 0,1 e leva 3, e apri su "ETH" senza direzione
    Quando il flusso "alfa" esegue un ciclo
    Allora la decisione su "ETH" è scartata con il motivo "campo obbligatorio mancante: direzione"
    E la decisione su "BTC" prosegue al controllo del rischio

  Schema dello scenario: Motivi di non conformità
    Dato che l'agente risponde su "BTC" <decisione>
    Quando il flusso "alfa" esegue un ciclo
    Allora la decisione su "BTC" è scartata con il motivo "<motivo>"

    Esempi:
      | decisione                          | motivo                                 |
      | apri long con quota 1,5 e leva 3   | valore fuori dall'intervallo: quota    |
      | apri long con quota "tanta" e leva 3 | valore di tipo non ammesso: quota    |
      | raddoppia                          | azione non ammessa: raddoppia          |

  Scenario: Asset estraneo al flusso
    Dato che l'agente risponde anche apri long su "DOGE"
    Quando il flusso "alfa" esegue un ciclo
    Allora la decisione su "DOGE" è scartata con il motivo "asset non del flusso: DOGE"

  Scenario: Asset senza decisione
    Dato che l'agente risponde solo per "BTC" e "ETH"
    Quando il flusso "alfa" esegue un ciclo
    Allora per "SOL" il ciclo registra una decisione mancante trattata come mantieni

  Scenario: Risposta non leggibile
    Dato che l'agente risponde con un testo che non segue il formato della risposta
    Quando il flusso "alfa" esegue un ciclo
    Allora il ciclo registra la risposta integrale dell'agente
    E il ciclo registra tutte le decisioni come scartate con il motivo "risposta non leggibile"
    E il ciclo non invia ordini all'exchange
