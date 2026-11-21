# language: it
@R5.1.1
Funzionalità: R5.1.1 Grandi trasferimenti (whale)
  Come utente
  Voglio che l'agente sappia dei grandi trasferimenti di criptovalute
  Perché spesso anticipano movimenti di prezzo

  Nuova fonte di mercato "whale" con un adapter, Arkham (chiave gratuita, da configurare in Impostazioni ›
  Chiavi, R4.1.2). Per ogni ciclo entrano nel contesto i trasferimenti dell'ultimo intervallo del flusso sopra una
  soglia di controvalore (parametro dell'adapter, predefinito 1.000.000 USD): data e ora, asset, quantità,
  controvalore, descrizione di origine e destinazione quando nota (RF-11.01). Senza trasferimenti sopra soglia
  il contesto lo dice; la fonte non è assente.

  Fuori ambito: altri adapter whale (Whale Alert, grandi ordini su Hyperliquid), aggiungibili in seguito.

  Contesto:
    Dato che il flusso "alfa" ha intervallo 60 minuti e la fonte "whale" con l'adapter "Arkham" configurato

  Scenario: Trasferimenti sopra soglia nel contesto
    Dato che nell'ultima ora c'è stato un trasferimento di 500 BTC da un wallet a un exchange
    Quando parte il ciclo di "alfa"
    Allora il contesto contiene il trasferimento con data e ora, asset, quantità, controvalore e descrizione

  Scenario: Trasferimenti sotto soglia esclusi
    Dato che nell'ultima ora ci sono stati solo trasferimenti sotto 1.000.000 USD
    Quando parte il ciclo di "alfa"
    Allora il contesto dice "nessun grande trasferimento nell'ultimo intervallo"

  Scenario: Fornitore che non risponde
    Dato che Arkham non risponde
    Quando parte il ciclo di "alfa"
    Allora la fonte "whale" è assente nel contesto e il ciclo prosegue
