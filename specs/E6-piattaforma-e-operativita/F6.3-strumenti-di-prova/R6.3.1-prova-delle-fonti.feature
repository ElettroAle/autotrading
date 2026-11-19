# language: it
@R6.3.1
Funzionalità: R6.3.1 Prova delle fonti
  Come utente
  Voglio provare una fonte e vederne subito l'esito
  Perché so se le chiamate alle fonti funzionano prima di affidarle a un flusso

  Nella dashboard una pagina Fonti elenca le fonti del catalogo (R1.3.1). Per ogni fonte l'utente sceglie asset e
  parametri (con i valori predefiniti della fonte) e preme Prova: la piattaforma esegue la stessa lettura del ciclo e
  mostra esito (riuscita o errore), valori letti, istante di riferimento dei dati e tempo di risposta. Un errore mostra
  il motivo, se è transitorio o permanente, come nel ciclo (R1.2.5). La prova non registra valori nei cicli e non tocca
  i flussi. Con le fonti ad adapter (R4.1.1) la prova diventa per adapter e usa le credenziali del tenant (R4.1.2).

  Contesto:
    Dato che "anna" è nella pagina Fonti della dashboard

  Scenario: Prova riuscita
    Quando "anna" prova la fonte "indicatori" per l'asset "BTC" con i parametri predefiniti
    Allora vede l'esito "riuscita", i valori letti, l'istante dei dati e il tempo di risposta

  Scenario: Prova fallita
    Dato che la fonte "notizie" non risponde
    Quando "anna" prova la fonte "notizie"
    Allora vede l'esito "errore" con il motivo e l'indicazione "transitorio"

  Scenario: Parametri non validi
    Quando "anna" prova la fonte "indicatori" con un periodo fuori dai limiti
    Allora la prova non parte e il parametro mostra il limite ammesso

  Scenario: La prova non tocca i flussi
    Dato che "anna" ha il flusso "alfa" con la fonte "indicatori"
    Quando "anna" prova la fonte "indicatori"
    Allora i cicli del flusso "alfa" non registrano valori della prova
