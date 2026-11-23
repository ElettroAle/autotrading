# language: it
@R5.1.6
Funzionalità: R5.1.6 Parametri a lista per le fonti di mercato
  Come utente
  Voglio scegliere io periodi, orizzonti e finestre di ogni valore che le fonti danno all'agente, come liste di numeri
  Perché una strategia nuova si provi cambiando la configurazione del flusso e non il codice

  Regole comuni a ogni parametro a lista: una lista di interi, ogni valore produce il suo gruppo di valori nel
  contesto; lista vuota: quel valore non si calcola e i dati che servono solo a lui non si leggono; la lista si salva
  ordinata e senza doppioni; ogni parametro dichiara intervallo ammesso e numero massimo di valori; il nome di ogni
  valore nel contesto porta il numero che lo ha generato; un valore che lo storico non permette di calcolare compare
  tra i dati mancanti, gli altri della stessa lista arrivano comunque; i valori giornalieri usano solo giornate UTC
  chiuse; un parametro a lista nuovo si aggiunge dichiarandolo nella fonte: API, controllo e dashboard lo ricavano
  dalla dichiarazione, senza codice dedicato. Il requisito è agnostico rispetto all'exchange: nessun limite deriva da
  quante candele conserva un mercato. Gann e ciclo sono liste come Fibonacci; MACD e timeframe restano come oggi.

  Scenario: Un parametro a lista nuovo non richiede codice dedicato
    Dato che una fonte dichiara un parametro a lista con nome, intervallo e numero massimo di valori
    Quando "anna" apre la configurazione della fonte nella dashboard
    Allora il campo del parametro compare con il suo intervallo
    E il salvataggio lo controlla con le regole comuni

  Scenario: Editor della dashboard
    Quando "anna" scrive 7, 30, 90 nel campo "tendenza giorni"
    Allora la fonte è salvata con tendenza_giorni [7, 30, 90]
