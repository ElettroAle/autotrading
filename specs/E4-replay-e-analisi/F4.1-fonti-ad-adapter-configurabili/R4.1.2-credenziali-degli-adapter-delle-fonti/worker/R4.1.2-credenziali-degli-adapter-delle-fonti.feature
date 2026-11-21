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

  Scenario: Credenziale rifiutata nel ciclo
    Dato che il flusso "alfa" usa l'adapter "LunarCrush"
    Quando nel ciclo il fornitore rifiuta la chiave
    Allora l'adapter "LunarCrush" è assente nel contesto del ciclo con il motivo
    E "anna" riceve un avviso

  Scenario: Un solo avviso per la credenziale rifiutata
    Dato che il flusso "alfa" usa l'adapter "LunarCrush"
    E che nel ciclo il fornitore ha rifiutato la chiave e "anna" ne ha ricevuto l'avviso
    Quando nel ciclo successivo il fornitore rifiuta ancora la chiave
    Allora "anna" non riceve un altro avviso per l'adapter "LunarCrush"
    E l'adapter "LunarCrush" è assente nel contesto del ciclo con il motivo
