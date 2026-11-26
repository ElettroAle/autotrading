# language: it
@R5.5.5
Funzionalità: R5.5.5 Esposizione nella stessa direzione tra i flussi del conto
  Come utente
  Voglio poter limitare quanto i flussi di un conto, sommati, sono esposti nella stessa direzione, e poter mostrare a un
  agente l'esposizione degli altri flussi del conto
  Perché i flussi di un conto non finiscano esposti tutti nella stessa direzione senza che nessuno lo sappia

  I limiti di esposizione valgono per il singolo flusso (R1.5.1, R3.2.1). Nessun limite e nessun dato riguarda l'insieme
  dei flussi di un conto: il 25 novembre 2026 quattro flussi dello stesso conto erano tutti short insieme, e nessun
  agente lo sapeva.

  Impostazioni, facoltative e vuote o spente di default. Con i default conto e flussi si comportano come oggi.
  - Sul conto, esposizione massima per direzione: percentuale maggiore di 0 del saldo del conto letto dall'exchange.
  - Sul flusso, esposizione del conto nel contesto dell'agente: opzione, spenta di default.

  Regole.
  - L'esposizione long del conto è la somma dei valori (dimensione per prezzo di mercato) delle posizioni long di tutti
    i flussi non archiviati del conto; lo stesso per lo short. Le due direzioni non si compensano. Le posizioni che
    nessun flusso spiega non contano.
  - Un'apertura è bloccata, col motivo, quando l'esposizione del conto in quella direzione più il valore dell'apertura
    supera il limite. Un'apertura che porta esattamente al limite passa. Non c'è riduzione dell'apertura, nemmeno con
    «porta al minimo».
  - Di un'inversione bloccata si esegue la sola chiusura della posizione aperta.
  - Il limite si imposta e si toglie dal conto, da API e dashboard.
  - Con l'opzione accesa, lo stato inviato all'agente riporta l'esposizione long e short degli altri flussi del conto,
    escluso il flusso stesso.

  Fuori ambito: limite sull'esposizione netta (long meno short), limite tra conti diversi, impostazione del limite dagli
  strumenti MCP.

  Contesto:
    Dato che "anna" ha il conto "principale" con i flussi "alfa", "beta" e "gamma"

  Scenario: Conti già esistenti
    Dato che il conto "principale" esisteva prima del limite di esposizione per direzione
    Quando "anna" legge il conto "principale"
    Allora il conto "principale" non ha esposizione massima per direzione

  Scenario: Limite non positivo
    Quando "anna" imposta l'esposizione massima per direzione del conto "principale" a 0%
    Allora la modifica viene rifiutata con "l'esposizione massima per direzione è maggiore di 0"

  Scenario: Limite impostato e tolto
    Quando "anna" imposta l'esposizione massima per direzione del conto "principale" a 60%
    Allora il conto "principale" ha esposizione massima per direzione 60%
    Quando "anna" toglie l'esposizione massima per direzione del conto "principale"
    Allora il conto "principale" non ha esposizione massima per direzione

  Scenario: Opzione del flusso spenta di default
    Quando "anna" crea il flusso "delta" senza indicare l'esposizione del conto nel contesto dell'agente
    Allora il flusso "delta" ha l'esposizione del conto nel contesto dell'agente spenta

  Scenario: L'opzione del flusso crea una versione
    Quando "anna" accende per "alfa" l'esposizione del conto nel contesto dell'agente
    Allora "alfa" ha una nuova versione della configurazione con l'esposizione del conto nel contesto dell'agente accesa
