# language: it
@R1.3.7
Funzionalità: R1.3.7 Fonte notizie
  Come utente
  Voglio che l'agente riceva le notizie cripto più recenti
  Perché tenga conto degli eventi che muovono il mercato

  A ogni ciclo la fonte raccoglie le notizie cripto più recenti, ciascuna con titolo, data e ora di
  pubblicazione e sintesi. Le notizie riguardano il mercato cripto in generale e compaiono una sola volta nel
  contesto, dalla più recente alla meno recente.
  Parametri per flusso: numero di notizie, da 1 a 50, predefinito 10; età massima in ore, da 1 a 168,
  predefinita 24. Una notizia più vecchia dell'età massima non entra nel contesto.

  Fuori ambito: messaggi social di persone influenti, notizie filtrate per asset.

  Contesto:
    Dato che "anna" ha il flusso "alfa" con la fonte "notizie" attiva
    E che sono disponibili 30 notizie pubblicate nelle ultime 48 ore, 15 delle quali nelle ultime 24 ore

  Schema dello scenario: Numero di notizie ed età massima fuori dall'intervallo
    Quando "anna" imposta sul flusso "alfa" la fonte "notizie" con <parametro> <valore>
    Allora la modifica è rifiutata con il motivo "parametro fuori dai valori ammessi: <parametro>, <ammessi>"

    Esempi:
      | parametro       | valore | ammessi     |
      | numero notizie  | 0      | da 1 a 50   |
      | numero notizie  | 51     | da 1 a 50   |
      | età massima ore | 0      | da 1 a 168  |
      | età massima ore | 169    | da 1 a 168  |
