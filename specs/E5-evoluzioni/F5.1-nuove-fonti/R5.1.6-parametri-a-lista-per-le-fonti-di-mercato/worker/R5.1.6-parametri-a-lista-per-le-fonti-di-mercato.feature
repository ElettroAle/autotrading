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

  Scenario: Periodi delle medie e dell'RSI scelti dall'utente
    Dato un flusso con la fonte indicatori, medie_periodi [10, 200] e rsi_periodi [21]
    Quando parte un ciclo
    Allora il contesto contiene EMA10, EMA200, MA10, MA200 e RSI21, e nessun'altra media o RSI

  Scenario: Orizzonti della tendenza scelti dall'utente
    Dato tendenza_giorni [3, 90] e canale_giorni [10]
    Quando parte un ciclo
    Allora il contesto contiene la variazione a 3 e a 90 giorni e il canale a 10 giorni

  Scenario: La variazione si calcola sulle chiusure giornaliere
    Dato tendenza_giorni [30]
    E la chiusura giornaliera di 30 giorni fa a 50000 e l'ultima a 55000
    Quando parte un ciclo
    Allora la variazione a 30 giorni è 10

  Scenario: Il canale dà massimo, minimo e punto medio
    Dato canale_giorni [20]
    E venti giornate chiuse con massimo 110 e minimo 90
    Quando parte un ciclo
    Allora il contesto contiene per il canale a 20 giorni massimo 110, minimo 90 e punto medio 100

  Scenario: Volume relativo dell'ultima candela chiusa
    Dato volume_relativo_candele [42]
    E l'ultima candela chiusa del timeframe lungo con volume 300 e le 42 precedenti con media 100
    Quando parte un ciclo
    Allora il contesto contiene il volume relativo a 42 candele del timeframe lungo uguale a 3
    E quello del timeframe breve calcolato allo stesso modo sulle sue candele

  Scenario: Più finestre per gli indicatori estesi
    Dato fibonacci_candele [100, 200], gann_candele [100] e ciclo_candele [200]
    Quando parte un ciclo
    Allora il contesto contiene i livelli di Fibonacci su 100 e su 200 candele, gli angoli di Gann su 100 e il ciclo dominante su 200

  Scenario: Orizzonti del forecast liberi
    Dato orizzonti_minuti [15, 240, 1440]
    Quando parte un ciclo
    Allora il contesto contiene il forecast a 15 minuti, 4 ore e 1 giorno

  Scenario: Pivot su più periodi
    Dato pivot_giorni [1, 7]
    Quando parte un ciclo
    Allora il contesto contiene i pivot del giorno precedente e dei 7 giorni precedenti

  Scenario: Lista vuota spegne il valore
    Dato tendenza_giorni [] e canale_giorni []
    Quando parte un ciclo
    Allora il contesto non contiene valori di tendenza e la fonte non legge candele giornaliere

  Scenario: La giornata in corso non conta
    Dato tendenza_giorni [7] e canale_giorni [20]
    E la giornata UTC corrente non ancora chiusa
    Quando parte un ciclo
    Allora variazione e canale usano come ultima chiusura quella della giornata precedente

  Scenario: Storico insufficiente per un valore della lista
    Dato tendenza_giorni [7, 90] e un adapter del mercato che dà solo 40 giornate chiuse
    Quando parte un ciclo
    Allora il contesto contiene la variazione a 7 giorni
    E la variazione a 90 giorni compare tra i dati mancanti
