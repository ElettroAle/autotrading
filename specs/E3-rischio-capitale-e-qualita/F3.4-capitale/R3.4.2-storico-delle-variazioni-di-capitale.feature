# language: it
@R3.4.2 @wip
Funzionalità: R3.4.2 Storico delle variazioni di capitale
  Come utente
  Voglio lo storico di ogni variazione del capitale dei miei flussi e dei miei conti
  Perché ricostruisco quando e perché il capitale è cambiato

  Ogni aumento e ogni riduzione del capitale allocato (R1.1.7) e ogni incasso (R3.4.1) si registra con data, ora,
  flusso, motivo ("aumento", "riduzione", "incasso"), importo, capitale allocato prima e dopo (RF-22.07).
  Lo storico del flusso elenca le sue variazioni; lo storico del conto elenca quelle di tutti i suoi flussi e i
  depositi e i prelievi che l'exchange dichiara sul conto, con motivo "deposito" o "prelievo".
  Lo storico si consulta dall'interfaccia programmatica e dalla dashboard, a pagine dalla variazione più recente, e si
  filtra per periodo.
  Le variazioni appartengono al tenant.

  Contesto:
    Dato che "anna" ha sul conto "test-1" i flussi "alfa" con capitale allocato 500 USDC e "beta" con capitale allocato 300 USDC
  Schema dello scenario: Variazione del capitale allocato registrata
    Quando "anna" porta il capitale allocato di "alfa" a <dopo> USDC
    Allora lo storico delle variazioni di "alfa" contiene "<motivo>" di <importo> USDC, da 500 a <dopo> USDC, con data e ora
    Esempi:
      | dopo | motivo    | importo |
      | 700  | aumento   | 200     |
      | 400  | riduzione | 100     |
  Scenario: Incasso registrato
    Dato che "alfa" ha valore complessivo 618 USDC senza posizioni aperte
    Quando "anna" incassa i profitti di "alfa"
    Allora lo storico delle variazioni di "alfa" contiene "incasso" di 118 USDC, da 500 a 500 USDC, con data e ora
  Scenario: Storico del conto
    Dato che "anna" ha aumentato di 200 USDC il capitale di "alfa" e ridotto di 100 USDC quello di "beta"
    Quando "anna" consulta lo storico delle variazioni del conto "test-1"
    Allora lo storico contiene l'aumento di "alfa" e la riduzione di "beta", dalla più recente
  Schema dello scenario: Deposito o prelievo del conto
    Dato che l'exchange dichiara sul conto "test-1" un <movimento> di <importo> USDC
    Quando "anna" consulta lo storico delle variazioni del conto "test-1"
    Allora lo storico contiene "<movimento>" di <importo> USDC con data e ora dell'exchange
    Esempi:
      | movimento | importo |
      | deposito  | 500     |
      | prelievo  | 300     |
  Scenario: Filtro per periodo
    Dato che "alfa" ha una variazione del 10/11/2026 e una del 15/11/2026
    Quando "anna" consulta lo storico delle variazioni di "alfa" dal 14/11/2026 al 16/11/2026
    Allora lo storico contiene solo la variazione del 15/11/2026
  Scenario: Storico nella dashboard
    Dato che "anna" ha aumentato di 200 USDC il capitale di "alfa"
    Quando "anna" apre nella dashboard lo storico delle variazioni di "alfa"
    Allora la tabella mostra data e ora, motivo "aumento", importo 200 USDC, capitale prima 500 USDC e dopo 700 USDC
  Scenario: Variazioni di un altro tenant
    Dato che "bruno" ha una variazione di capitale su un suo flusso
    Quando "anna" consulta lo storico delle variazioni del conto "test-1"
    Allora lo storico non contiene la variazione di "bruno"
