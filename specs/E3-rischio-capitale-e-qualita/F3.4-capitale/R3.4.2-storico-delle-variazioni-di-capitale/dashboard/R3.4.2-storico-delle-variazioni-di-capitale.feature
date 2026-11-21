# language: it
@R3.4.2
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
  Scenario: Storico nella dashboard
    Dato che "anna" ha aumentato di 200 USDC il capitale di "alfa"
    Quando "anna" apre nella dashboard lo storico delle variazioni di "alfa"
    Allora la tabella mostra data e ora, motivo "aumento", importo 200 USDC, capitale prima 500 USDC e dopo 700 USDC
