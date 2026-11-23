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

  Scenario: Valori ordinati e senza doppioni
    Quando "anna" salva medie_periodi [50, 20, 50]
    Allora la configurazione salvata ha medie_periodi [20, 50]

  Schema dello scenario: Valore fuori intervallo
    Quando "anna" salva <parametro> <valori>
    Allora il salvataggio è rifiutato con motivo "<motivo>"

    Esempi:
      | parametro               | valori | motivo                                              |
      | medie_periodi           | [1]    | medie periodi: ogni valore tra 2 e 10000              |
      | rsi_periodi             | [1]    | rsi periodi: ogni valore tra 2 e 10000                |
      | tendenza_giorni         | [0]    | tendenza giorni: ogni valore tra 1 e 3650            |
      | canale_giorni           | [1]    | canale giorni: ogni valore tra 2 e 3650              |
      | volume_relativo_candele | [1]    | volume relativo candele: ogni valore tra 2 e 10000    |
      | fibonacci_candele       | [5]    | fibonacci candele: ogni valore tra 10 e 10000         |
      | gann_candele            | [5]    | gann candele: ogni valore tra 10 e 10000              |
      | ciclo_candele           | [5]    | ciclo candele: ogni valore tra 10 e 10000             |
      | pivot_giorni            | [0]    | pivot giorni: ogni valore tra 1 e 3650                |
      | orizzonti_minuti        | [1]    | orizzonti minuti: ogni valore tra 15 e 43200        |

  Scenario: Troppi valori in una lista
    Quando "anna" salva tendenza_giorni con 9 valori
    Allora il salvataggio è rifiutato con motivo "tendenza giorni: al massimo 8 valori"
