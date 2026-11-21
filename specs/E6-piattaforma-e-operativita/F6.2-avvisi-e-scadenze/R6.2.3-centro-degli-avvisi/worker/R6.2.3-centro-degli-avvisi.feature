# language: it
@R6.2.3
Funzionalità: R6.2.3 Centro degli avvisi
  Come utente
  Voglio vedere in un solo posto tutto ciò che chiede un mio intervento, da qualunque parte arrivi
  Perché non mi sfugga un problema e capisca subito dove intervenire

  Un avviso è un fatto che chiede un intervento dell'utente; ha una gravità, uno stato e la risorsa interessata
  (conto, flusso o chiave). Le notifiche restano il racconto cronologico di ciò che succede (R1.8.2, R6.2.1): un
  avviso nasce insieme alla sua notifica, ma non ogni notifica è un avviso.
  Sono avvisi:
  - allarme di riconciliazione del conto (R3.3.1): gravità critica, si risolve con la conferma del saldo;
  - flusso in pausa automatica (R1.2.4, R1.6.2): gravità critica, si risolve quando il flusso riprende, si ferma o
    si archivia;
  - posizione su un asset di nessun flusso (R1.6.2): gravità attenzione, si risolve quando la posizione non c'è più;
  - esecuzione senza identificativo della piattaforma (R1.6.2): gravità attenzione, la risolve l'utente;
  - chiave in scadenza (R6.2.2): gravità attenzione, critica dalla scadenza, si risolve quando la chiave è rinnovata
    o rimossa.
  Non sono avvisi le variazioni del saldo entro la soglia del conto: restano nel registro del conto (Bug 596).
  Stati: aperto e risolto. Un avviso si risolve da solo quando la sua causa sparisce; l'utente risolve a mano solo
  quelli che non hanno una risoluzione automatica.
  La pagina Avvisi è una voce del menu con il numero degli avvisi aperti. Elenca gli avvisi dal più recente con
  gravità (icona e testo), titolo, risorsa interessata con il collegamento, istante di apertura e stato; i filtri
  per stato (predefinito: aperti), gravità, tipo di risorsa e periodo usano il componente condiviso. Il dettaglio di
  un avviso mostra che cosa è successo con i valori letti, che cosa fare con i comandi che lo risolvono (conferma del
  saldo, ripresa del flusso, rinnovo della chiave) e il collegamento alla risorsa. La pagina Allarmi del conto di oggi
  confluisce negli avvisi filtrati per quel conto; la soglia e lo stato della riconciliazione restano nel riquadro
  del conto, in Conti. Il collegamento nella notifica di un avviso porta al suo dettaglio (R3.5.6).
  Gli avvisi appartengono al tenant e si conservano 90 giorni dopo la risoluzione.

  Fuori ambito: lo stato «preso in carico» (piattaforma personale, un utente per tenant); regole di avviso
  configurabili dall'utente oltre alla soglia del conto.

  Contesto:
    Dato che "anna" ha il conto "test-1" con il flusso attivo "alfa"

  Scenario: Variazione del saldo entro la soglia
    Dato che il saldo del conto "test-1" si discosta da quello atteso entro la soglia
    Quando il flusso "alfa" esegue un ciclo
    Allora non si apre alcun avviso
    E "anna" non riceve alcuna notifica

  Scenario: Dalla notifica al dettaglio
    Dato che "anna" ha collegato Telegram
    Quando si apre l'avviso di una posizione su un asset di nessun flusso
    Allora la notifica porta al dettaglio dell'avviso
