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

  Scenario: Opzione del flusso dagli strumenti
    Quando il client MCP di "anna" accende per "alfa" l'esposizione del conto nel contesto dell'agente
    Allora il dettaglio di "alfa" letto dagli strumenti riporta l'esposizione del conto nel contesto dell'agente accesa

  Scenario: Limite del conto letto dagli strumenti
    Dato che il conto "principale" ha esposizione massima per direzione 60%
    Quando il client MCP di "anna" legge i conti
    Allora il conto "principale" riporta esposizione massima per direzione 60%
