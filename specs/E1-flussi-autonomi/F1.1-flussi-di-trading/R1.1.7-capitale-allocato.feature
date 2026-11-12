# language: it
@R1.1.7
Funzionalità: R1.1.7 Variazione del capitale allocato
  Come utente
  Voglio aumentare o ridurre il capitale allocato a un flusso in qualsiasi momento
  Perché la quota di conto su cui opera ogni flusso segua le mie scelte

  Il capitale libero di un conto è il saldo letto dall'exchange meno la somma dei capitali allocati ai suoi flussi
  non archiviati. Un aumento non supera il capitale libero del conto. Una riduzione non porta sotto zero la
  liquidità disponibile del flusso: capitale allocato più PnL realizzato dai suoi ordini, meno le loro commissioni,
  meno il margine che l'exchange dichiara impegnato nelle sue posizioni aperte (R1.6.1). Il capitale minimo del
  flusso è quello che porta questa liquidità a zero.
  La variazione vale in ogni stato del flusso tranne archiviato, ha effetto dal ciclo successivo ed è registrata
  con data e ora, importo precedente, importo nuovo e utente.

  Fuori ambito: l'incasso dei profitti e il prelievo dall'exchange.

  Contesto:
    Dato che "anna" ha il conto "test-1" con saldo 1000 USDC
    E che "anna" ha il flusso "alfa" sul conto "test-1" con capitale allocato 400 USDC e 150 USDC impegnati come margine

  Scenario: Aumento entro il capitale libero
    Quando "anna" porta il capitale allocato del flusso "alfa" a 700 USDC
    Allora il flusso "alfa" ha capitale allocato 700 USDC
    E il capitale libero del conto "test-1" è 300 USDC
    E la variazione da 400 a 700 USDC è registrata nello storico del flusso "alfa"

  Scenario: Aumento oltre il capitale libero
    Quando "anna" porta il capitale allocato del flusso "alfa" a 1100 USDC
    Allora la variazione è rifiutata con il motivo "capitale allocato oltre il capitale disponibile: 1000 USDC"
    E il flusso "alfa" ha capitale allocato 400 USDC

  Scenario: Riduzione entro la liquidità disponibile del flusso
    Quando "anna" porta il capitale allocato del flusso "alfa" a 200 USDC
    Allora il flusso "alfa" ha capitale allocato 200 USDC
    E il capitale libero del conto "test-1" è 800 USDC

  Scenario: Riduzione sotto il margine impegnato
    Quando "anna" porta il capitale allocato del flusso "alfa" a 100 USDC
    Allora la variazione è rifiutata con il motivo "capitale allocato sotto il minimo del flusso: 150 USDC"
    E il flusso "alfa" ha capitale allocato 400 USDC

  Scenario: Il margine impegnato è quello dichiarato dall'exchange
    Dato che l'exchange dichiara 180 USDC di margine per la posizione del flusso "alfa"
    Quando "anna" porta il capitale allocato del flusso "alfa" a 160 USDC
    Allora la variazione è rifiutata con il motivo "capitale allocato sotto il minimo del flusso: 180 USDC"
    E il flusso "alfa" ha capitale allocato 400 USDC

  Scenario: Riduzione che porterebbe la liquidità del flusso sotto zero
    Dato che il flusso "alfa" ha realizzato -200 USDC con 10 USDC di commissioni
    Quando "anna" porta il capitale allocato del flusso "alfa" a 300 USDC
    Allora la variazione è rifiutata con il motivo "capitale allocato sotto il minimo del flusso: 360 USDC"
    E il flusso "alfa" ha capitale allocato 400 USDC

  Scenario: Riduzione fino al minimo del flusso dopo le perdite
    Dato che il flusso "alfa" ha realizzato -200 USDC con 10 USDC di commissioni
    Quando "anna" porta il capitale allocato del flusso "alfa" a 360 USDC
    Allora il flusso "alfa" ha capitale allocato 360 USDC

  Scenario: La variazione ha effetto dal ciclo successivo
    Dato che un ciclo del flusso "alfa" è in corso con capitale allocato 400 USDC
    Quando "anna" porta il capitale allocato del flusso "alfa" a 700 USDC
    Allora il ciclo in corso si conclude con capitale allocato 400 USDC
    E il ciclo successivo del flusso "alfa" usa capitale allocato 700 USDC
