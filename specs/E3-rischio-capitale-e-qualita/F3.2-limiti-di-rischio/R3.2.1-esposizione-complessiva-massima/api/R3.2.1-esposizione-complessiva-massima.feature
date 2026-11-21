# language: it
@R3.2.1
Funzionalità: R3.2.1 Esposizione complessiva massima
  Come utente
  Voglio un limite alla somma delle posizioni aperte di un flusso
  Perché il flusso non impegna tutto il capitale anche se ogni operazione rispetta il suo limite

  Ogni flusso può avere due limiti di esposizione complessiva, facoltativi, in percentuale dei soldi del flusso
  (la stessa base dei limiti per operazione, R1.5.1): uno sul margine impegnato da tutte le posizioni aperte, uno sul
  valore di tutte le posizioni aperte. Ciascuno va da 0,1 a 1000.
  Un'apertura che porterebbe la somma oltre un limite viene ridotta al residuo; con entrambi i limiti vale il più
  restrittivo. Se il residuo è nullo l'apertura non viene eseguita (RF-18.03). Un residuo sotto l'importo minimo
  dell'exchange segue la regola del minimo (R1.5.4).
  Il limite complessivo si applica dopo quello per operazione. Le aperture dello stesso ciclo consumano il residuo
  nell'ordine in cui si eseguono.
  Ogni riduzione e ogni blocco si registra con la decisione originale, quella eseguita e il motivo (RF-18.10).
  Modificare i limiti crea una versione della configurazione (R1.1.3).

  Contesto:
    Dato che "anna" ha il flusso "alfa" attivo con asset "BTC", "ETH" e "SOL" e soldi del flusso per 1000 USDC

  Schema dello scenario: Limite complessivo fuori dall'intervallo
    Quando "anna" imposta l'esposizione complessiva massima del margine di "alfa" a <valore>%
    Allora la modifica viene rifiutata con "l'esposizione complessiva massima va da 0,1 a 1000"
    Esempi:
      | valore |
      | 0      |
      | 1001   |

  Schema dello scenario: Limite complessivo sul valore fuori dall'intervallo
    Quando "anna" imposta l'esposizione complessiva massima del valore di "alfa" a <valore>%
    Allora la modifica viene rifiutata con "l'esposizione complessiva massima va da 0,1 a 1000"

    Esempi:
      | valore |
      | 0      |
      | 1001   |

  Scenario: La modifica dei limiti complessivi crea una versione
    Quando "anna" imposta l'esposizione complessiva massima del margine di "alfa" a 40%
    Allora la configurazione di "alfa" passa alla versione 2 con esposizione complessiva massima del margine 40%
