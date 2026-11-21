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

  Scenario: Prezzo effettivo letto dall'exchange da cui viene la previsione
    Dato che alle 10:00 un ciclo di "alfa" ha previsto "BTC" a 1 ora dai prezzi dell'exchange, con ultimo prezzo 60000
    Quando arrivano le 11:00 e l'exchange quota "BTC" 60300
    Allora la previsione delle 10:00 di "alfa" su "BTC" a 1 ora ha il prezzo effettivo 60300 dello stesso exchange
