# language: it
@R4.1.2
Funzionalità: R4.1.2 Credenziali degli adapter delle fonti
  Come utente
  Voglio inserire una sola volta le credenziali di un adapter di fonte
  Perché le uso in tutti i miei flussi senza ripeterle

  In Impostazioni › Chiavi una sezione "Fonti" elenca gli adapter che richiedono configurazione, con i campi
  dichiarati dall'adapter (R4.1.1); i campi segreti si salvano cifrati come le chiavi dei fornitori IA, li legge
  solo il worker e non si mostrano mai in chiaro. Le credenziali appartengono al tenant. Un adapter che richiede
  configurazione e non ce l'ha resta nell'elenco del flusso ma non è attivabile, con il motivo. Se nel ciclo il
  fornitore rifiuta la credenziale, quell'adapter è una fonte assente (R1.2.5) e l'utente è avvisato una volta.

  Questo lavoro lega anche lo scenario «Scadenza sconosciuta» di R6.2.2
  (specs/E6-piattaforma-e-operativita/F6.2-avvisi-e-scadenze/R6.2.2-avviso-di-scadenza-delle-chiavi.feature),
  oggi @wip perché richiede le credenziali delle fonti: va definito il suo passo e tolto @wip.

  Fuori ambito: limiti di spesa sui fornitori a pagamento.

  Contesto:
    Dato che "anna" è nella pagina delle chiavi
    E che esiste un adapter di fonte "LunarCrush" che richiede una "chiave API" segreta

  Scenario: Configurazione di un adapter
    Quando "anna" inserisce la chiave API dell'adapter "LunarCrush"
    Allora l'adapter "LunarCrush" risulta configurato
    E la chiave non è mostrata in chiaro

  Scenario: Adapter non configurato non attivabile
    Dato che l'adapter "LunarCrush" non è configurato
    Quando "anna" prova ad attivarlo nel flusso "alfa"
    Allora l'attivazione è rifiutata con il motivo "configura l'adapter LunarCrush in Impostazioni › Chiavi"

  Scenario: Adapter senza configurazione
    Quando "anna" apre la sezione "Fonti" delle chiavi
    Allora l'adapter "alternative.me" non è elencato tra quelli da configurare

  Scenario: Credenziali isolate per tenant
    Dato che "bruno" ha configurato l'adapter "LunarCrush"
    Quando "anna" apre la sezione "Fonti" delle chiavi
    Allora l'adapter "LunarCrush" risulta non configurato per "anna"
