# ADR 0061 — Chiusura manuale nello storico del flusso

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.7.2, R0.3.2
- Collegate: ADR 0047 (storico delle posizioni chiuse), 0055 (stop di un flusso), 0056 (notifiche e chiusure
  registrate dal ciclo)

## Contesto

R1.7.2 vuole nello storico di un flusso anche le posizioni che l'utente chiude a mano con il comando di R0.3.2, con
il motivo "comando manuale". Il comando manuale vive nel contesto `orders` (`ClosePositionUseCase`) e non sa nulla
dei flussi; la riconciliazione (ADR 0056) esclude apposta le chiusure fatte solo da ordini manuali della piattaforma,
perché le registra il comando manuale.

## Decisione

- **Caso d'uso nel contesto `flows`**: `RecordManualClosingUseCase` riceve conto, asset ed esecuzione della chiusura.
  Il flusso non archiviato del conto che ha l'asset nella configurazione (la regola di conflitto di R1.1.2 ne lascia
  al più uno) prende la chiusura: la posizione entra nel suo storico dall'ultima apertura del flusso sull'asset, con
  motivo `MANUAL`. Un asset che nessun flusso tratta, o una posizione che il flusso non ha mai aperto, non entra in
  nessuno storico; il secondo caso si registra nel log.
- **Ponte in `bootstrap.py`**: `ManualClosingsRecordedInFlows` avvolge la `PositionClosingPort` del comando manuale
  nell'API. Quando l'exchange conferma l'esecuzione (prezzo medio, istante e commissione presenti) chiama il caso
  d'uso; un rifiuto o un esito non confermato in tempo non registra nulla. L'esito torna all'utente invariato.
- La chiusura dello stop (ADR 0055) usa la porta non avvolta: registra già da sé con il suo motivo, quindi non c'è
  doppia registrazione.

## Alternative scartate

- **Registrare nel worker, dove l'ordine viene eseguito**: il worker esegue la chiusura per conto dell'API anche per
  lo stop e la verifica; distinguere lì il comando manuale vorrebbe dire portare il motivo della chiusura nel
  contratto HTTP tra API e worker.
- **Lasciare la chiusura manuale alla riconciliazione**: arriverebbe solo al ciclo successivo e il flusso fermo o in
  pausa non avrebbe cicli; inoltre l'ordine della piattaforma è noto, non serve dedurlo.
- **`ClosePositionUseCase` che chiama i flussi**: legherebbe il contesto `orders` al contesto `flows`.

## Conseguenze

- Dopo una chiusura manuale confermata, l'API legge i flussi e gli ordini del tenant e scrive una riga nello storico.
- Se la scrittura nello storico fallisce, la chiusura sull'exchange è comunque avvenuta e l'utente riceve l'errore:
  la posizione risulterà chiusa nello stato del flusso ma assente dallo storico.
