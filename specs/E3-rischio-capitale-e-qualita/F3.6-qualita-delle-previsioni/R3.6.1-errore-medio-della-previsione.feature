# language: it
@R3.6.1
Funzionalità: R3.6.1 Errore medio della previsione
  Come utente
  Voglio sapere di quanto sbaglia in media la previsione dei prezzi
  Perché decido quanto peso dare al forecast nei miei flussi

  Per ogni previsione registrata da un flusso (R1.3.5), allo scadere del suo orizzonte la piattaforma la confronta
  con il prezzo effettivo dell'asset in quell'istante, letto dall'exchange da cui viene la previsione, e ne calcola
  l'errore assoluto e l'errore percentuale sul prezzo effettivo (RF-26.01).
  Per un flusso, un asset e un orizzonte, nel periodo scelto, l'utente vede: l'errore medio assoluto, l'errore medio
  percentuale con due decimali, il numero di previsioni valutate e il numero di quelle non valutabili.
  Una previsione il cui orizzonte non è ancora scaduto non entra nel calcolo. Una previsione scaduta di cui manca il
  prezzo effettivo è non valutabile.
  I valori si consultano dall'interfaccia programmatica e nella pagina del flusso della dashboard.

  Fuori ambito: il grafico di previsione e prezzo (R4.3.1) e gli scostamenti anomali (R4.3.2).

  Contesto:
    Dato che "anna" ha il flusso "alfa" con la fonte forecast su "BTC" a 1 ora

  Scenario: Errore medio di due previsioni scadute
    Dato che "alfa" ha previsto 60500 per un istante in cui il prezzo effettivo è stato 60000
    E che "alfa" ha previsto 61000 per un istante in cui il prezzo effettivo è stato 61400
    Quando "anna" consulta l'errore della previsione di "alfa" su "BTC" a 1 ora
    Allora l'errore medio assoluto è 450
    E l'errore medio percentuale è 0,74%
    E le previsioni valutate sono 2

  Scenario: Previsione non ancora scaduta
    Dato che "alfa" ha una previsione scaduta con errore assoluto 500 e una previsione per un istante futuro
    Quando "anna" consulta l'errore della previsione di "alfa" su "BTC" a 1 ora
    Allora l'errore medio assoluto è 500
    E le previsioni valutate sono 1

  Scenario: Orizzonti separati
    Dato che "alfa" ha anche previsioni su "BTC" a 15 minuti con errore medio assoluto 900
    E che le previsioni di "alfa" su "BTC" a 1 ora hanno errore medio assoluto 450
    Quando "anna" consulta l'errore della previsione di "alfa" su "BTC" a 15 minuti
    Allora l'errore medio assoluto è 900

  Scenario: Prezzo effettivo mancante
    Dato che "alfa" ha una previsione scaduta con errore assoluto 500 e una previsione scaduta senza prezzo effettivo
    Quando "anna" consulta l'errore della previsione di "alfa" su "BTC" a 1 ora
    Allora le previsioni valutate sono 1
    E le previsioni non valutabili sono 1

  Scenario: Periodo scelto
    Dato che "alfa" ha una previsione del 10/11/2026 con errore assoluto 900 e una del 15/11/2026 con errore assoluto 300
    Quando "anna" consulta l'errore della previsione di "alfa" su "BTC" a 1 ora dal 14/11/2026 al 16/11/2026
    Allora l'errore medio assoluto è 300

  Scenario: Nessuna previsione nel periodo
    Dato che "alfa" non ha previsioni scadute nel periodo
    Quando "anna" consulta l'errore della previsione di "alfa" su "BTC" a 1 ora
    Allora l'errore è "non disponibile nel periodo"

  Scenario: Errore nella pagina del flusso
    Dato che le previsioni di "alfa" su "BTC" a 1 ora hanno errore medio assoluto 450 e percentuale 0,74% su 2 previsioni
    Quando "anna" apre la pagina del flusso "alfa" nella dashboard
    Allora la pagina mostra per "BTC" a 1 ora errore medio 450, 0,74%, 2 previsioni valutate

  Scenario: Prezzo effettivo letto dall'exchange da cui viene la previsione
    Dato che alle 10:00 un ciclo di "alfa" ha previsto "BTC" a 1 ora dai prezzi dell'exchange, con ultimo prezzo 60000
    Quando arrivano le 11:00 e l'exchange quota "BTC" 60300
    Allora la previsione delle 10:00 di "alfa" su "BTC" a 1 ora ha il prezzo effettivo 60300 dello stesso exchange
