# language: it
@R4.1.1
Funzionalità: R4.1.1 Fonti con adapter dichiarati
  Come utente
  Voglio che ogni fonte offra uno o più adapter, ciascuno con la configurazione che richiede
  Perché la stessa informazione si può prendere da fornitori diversi, come gli exchange e i fornitori IA

  Una fonte (indicatori, pivot, forecast, sentiment, notizie e quelle di E5) ha almeno un adapter. Ogni adapter
  dichiara: nome, descrizione, i propri parametri con valori predefiniti e ammessi, i campi di configurazione
  che richiede (nome, etichetta, segreto o no) oppure "nessuna configurazione necessaria", e se offre dati
  storici (usati dal replay, R4.2.2). L'API elenca fonti e adapter; la dashboard genera i moduli da questo
  elenco, come per exchange e fornitori IA (R2.3.8, R2.3.9).

  Nel flusso si attiva una fonte scegliendo uno o più dei suoi adapter, ciascuno con il proprio peso da 1 a 10
  e i propri parametri. I due sentiment di oggi (alternative.me e CoinMarketCap, ADR 0033) diventano due adapter
  della fonte "sentiment": le configurazioni esistenti dei flussi passano al nuovo modello conservando pesi e
  parametri, con una nuova versione della configurazione. Il contesto dell'agente nomina fonte e adapter di
  ogni dato.

  Fuori ambito: le nuove fonti (E5); le credenziali degli adapter (R4.1.2).

  Contesto:
    Dato che "anna" ha il flusso "alfa"

  Scenario: Elenco di fonti e adapter
    Quando "anna" chiede l'elenco delle fonti
    Allora la fonte "sentiment" ha gli adapter "alternative.me" e "CoinMarketCap"
    E ogni adapter dichiara parametri, configurazione richiesta e disponibilità dello storico
    E l'adapter "alternative.me" dichiara "nessuna configurazione necessaria"

  Scenario: Due adapter della stessa fonte nello stesso flusso
    Quando "anna" attiva nel flusso "alfa" la fonte "sentiment" con l'adapter "alternative.me" peso 3 e l'adapter "CoinMarketCap" peso 7
    Allora il contesto del prossimo ciclo contiene i due indici, ciascuno con il nome del suo adapter e il suo peso

  Scenario: Fonte attiva senza adapter
    Quando "anna" attiva nel flusso "alfa" la fonte "sentiment" senza scegliere un adapter
    Allora la configurazione è rifiutata con il motivo "scegli almeno un adapter della fonte sentiment"

  Scenario: Le configurazioni esistenti passano al nuovo modello
    Dato che il flusso "alfa" aveva le fonti "sentiment-alternative-me" peso 4 e "sentiment-coinmarketcap" peso 6
    Quando le fonti passano al modello ad adapter
    Allora il flusso "alfa" ha la fonte "sentiment" con l'adapter "alternative.me" peso 4 e l'adapter "CoinMarketCap" peso 6
    E la configurazione del flusso "alfa" ha una nuova versione

  Scenario: Parametro dell'adapter fuori dai valori ammessi
    Quando "anna" imposta un parametro dell'adapter "RSS" a un valore non ammesso
    Allora la configurazione è rifiutata con il motivo che nomina il parametro e i valori ammessi
