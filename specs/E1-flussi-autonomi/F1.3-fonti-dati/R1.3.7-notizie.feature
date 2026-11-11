# language: it
@R1.3.7 @wip
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

  Scenario: Notizie con i valori predefiniti
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene 10 notizie pubblicate nelle ultime 24 ore
    E ogni notizia riporta titolo, data e ora di pubblicazione e sintesi
    E le notizie sono ordinate dalla più recente

  Scenario: Età massima più restrittiva del numero
    Dato che il flusso "alfa" ha numero notizie 20 ed età massima 24 ore
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto contiene 15 notizie

  Scenario: Nessuna notizia recente
    Dato che il flusso "alfa" ha età massima 1 ora
    E che nessuna notizia è stata pubblicata nell'ultima ora
    Quando il flusso "alfa" esegue un ciclo
    Allora il contesto dichiara che non ci sono notizie nell'ultima ora
