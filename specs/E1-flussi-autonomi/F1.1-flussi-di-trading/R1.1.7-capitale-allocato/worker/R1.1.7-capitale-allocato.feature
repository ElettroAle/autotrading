# language: it
@R1.1.7
Funzionalità: R1.1.7 Variazione del capitale allocato
  Come utente
  Voglio aumentare o ridurre il capitale allocato a un flusso in qualsiasi momento
  Perché la quota di conto su cui opera ogni flusso segua le mie scelte

  Il capitale libero di un conto è il saldo letto dall'exchange meno il valore complessivo dei suoi flussi non
  archiviati (R1.1.1). Un aumento non supera il capitale libero del conto. Una riduzione non porta sotto zero la
  liquidità disponibile del flusso: capitale allocato più PnL realizzato dai suoi ordini, meno le loro commissioni,
  meno il margine che l'exchange dichiara impegnato nelle sue posizioni aperte (R1.6.1). Il capitale minimo del
  flusso è quello che porta questa liquidità a zero.
  La variazione vale in ogni stato del flusso tranne archiviato, ha effetto dal ciclo successivo ed è registrata
  con data e ora, importo precedente, importo nuovo e utente.

  Fuori ambito: l'incasso dei profitti e il prelievo dall'exchange.

  Contesto:
    Dato che "anna" ha il conto "test-1" con saldo 1000 USDC
    E che "anna" ha il flusso "alfa" sul conto "test-1" con capitale allocato 400 USDC e 150 USDC impegnati come margine

  Scenario: La variazione ha effetto dal ciclo successivo
    Dato che un ciclo del flusso "alfa" è in corso con capitale allocato 400 USDC
    Quando "anna" porta il capitale allocato del flusso "alfa" a 700 USDC
    Allora il ciclo in corso si conclude con capitale allocato 400 USDC
    E il ciclo successivo del flusso "alfa" usa capitale allocato 700 USDC
