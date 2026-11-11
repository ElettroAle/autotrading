# language: it
@R1.1.1
Funzionalità: R1.1.1 Creazione di un flusso
  Come utente
  Voglio creare un flusso di trading con la sua configurazione completa
  Perché un agente IA operi in autonomia su un mio conto con le regole che ho scelto

  La configurazione di un flusso comprende: nome, conto, asset, intervallo di ciclo, modello IA con i suoi
  parametri, fonti dati attive con pesi e parametri, istruzioni dell'agente, limiti di rischio, capitale allocato.
  L'intervallo di ciclo è un numero intero di minuti da 1 a 1440; senza indicazione vale 15 minuti.
  I limiti di rischio non hanno valori predefiniti: la leva massima è obbligatoria, e almeno uno dei due limiti
  di esposizione per operazione (sul margine impegnato o sul valore della posizione) è obbligatorio.
  Il capitale allocato non supera il capitale libero del conto: saldo letto dall'exchange meno le allocazioni
  degli altri flussi del conto.
  Un flusso appena creato è fermo: non esegue cicli finché l'utente non lo avvia.
  Una configurazione non valida è rifiutata per intero, con il motivo.

  Fuori ambito: la regola di conflitto sugli asset tra flussi dello stesso conto (R1.1.2), la duplicazione di un
  flusso, l'importazione e l'esportazione della configurazione.

  Contesto:
    Dato che "anna" ha il conto "test-1" con saldo 1000 USDC e nessun flusso
    E che il catalogo dei modelli contiene "openrouter/deepseek-chat"
    E che il catalogo delle fonti contiene "indicatori" e "notizie"
    E che "anna" ha registrato la chiave del fornitore "openrouter"

  Scenario: Creazione di un flusso valido
    Quando "anna" crea il flusso "alfa" sul conto "test-1" con asset "BTC, ETH", modello "openrouter/deepseek-chat", fonti "indicatori, notizie", leva massima 5, esposizione massima del margine 10% e capitale allocato 400 USDC
    Allora "anna" ha il flusso "alfa" nello stato "fermo"
    E il flusso "alfa" ha la versione di configurazione 1
    E il capitale libero del conto "test-1" è 600 USDC

  Scenario: Intervallo di ciclo predefinito
    Quando "anna" crea il flusso "alfa" senza indicare l'intervallo di ciclo
    Allora il flusso "alfa" ha l'intervallo di ciclo di 15 minuti

  Schema dello scenario: Configurazione non valida rifiutata
    Quando "anna" crea il flusso "alfa" con <difetto>
    Allora la creazione è rifiutata con il motivo "<motivo>"
    E "anna" non ha il flusso "alfa"

    Esempi:
      | difetto                                           | motivo                                              |
      | intervallo di ciclo 0 minuti                      | intervallo di ciclo fuori da 1-1440 minuti          |
      | intervallo di ciclo 1441 minuti                   | intervallo di ciclo fuori da 1-1440 minuti          |
      | modello "openai/inesistente"                      | modello non disponibile: openai/inesistente         |
      | fonte "oroscopo"                                  | fonte non disponibile: oroscopo                     |
      | asset "XYZ" non negoziabile sull'exchange del conto | asset non negoziabile sull'exchange: XYZ          |
      | nessun asset                                      | almeno un asset è obbligatorio                      |
      | nessuna leva massima                              | la leva massima è obbligatoria                      |
      | nessun limite di esposizione per operazione       | almeno un limite di esposizione è obbligatorio      |
      | capitale allocato 1200 USDC                       | capitale allocato oltre il capitale libero: 1000 USDC |
      | il nome "alfa" già usato da un suo flusso         | nome già usato da un altro flusso                   |
