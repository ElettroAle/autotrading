# ADR sorveglianza-del-prezzo-per-lo-stop-che-segue — Sorveglianza del prezzo e spostamento dello stop tra i cicli

- Stato: accettata (26 novembre 2026)
- Requisiti: US 749 R5.5.1 (Task 752)
- Collegate: ADR impostazioni-dello-stop-che-segue-il-prezzo, ADR aggiornamento-del-piano-di-uscita-di-una-posizione-aperta,
  ADR protezioni-ritentate-nel-ciclo, ADR 0112 (pianificazione dei cicli con APScheduler), ADR
  controllo-giornaliero-delle-scadenze, ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione, ADR 0007;
  `.claude/rules/context-flows.md`, `.claude/rules/context-orders.md`, `.claude/rules/tech-apscheduler.md`
- Verifica: prova

## Contesto e problema

Lo stop si sposta oggi solo con «aggiorna» dell'agente durante un ciclo. R5.5.1 chiede che la piattaforma controlli il
prezzo delle posizioni dei flussi con distanza o pareggio almeno una volta al minuto, indipendentemente dal ciclo, e
avvicini lo stop al prezzo senza mai allontanarlo.

## Fattori decisionali

- Regole di R5.5.1: miglior prezzo dall'apertura (o dal prezzo di mercato quando l'impostazione entra in vigore con la
  posizione aperta); tra stop in vigore e calcolato vale il più vicino al prezzo; una modifica delle impostazioni vale
  dal controllo successivo; chiusura dallo stop spostato con motivo «stop loss»; nessun prezzo in più controllato per i
  flussi senza impostazioni.
- Le credenziali dei conti le decifra solo il worker (ADR 0007): la sorveglianza gira nel worker.
- La sostituzione dello stop sull'exchange esiste già (R3.1.3) e registra il livello (ADR
  stop-e-obiettivo-in-vigore-nello-stato-della-posizione): si riusa, non si ripete.
- Un rifiuto dell'exchange si registra e il ciclo lo riporta (ADR protezioni-ritentate-nel-ciclo).

## Decisione

- **Regola nel domain.** `TrailingStop` calcola lo stop di una posizione da lato, prezzo d'ingresso, miglior prezzo e
  stop in vigore: lo stop a distanza dal miglior prezzo (solo dopo l'attivazione, se c'è), il prezzo d'ingresso dopo il
  pareggio, e tra questi e lo stop in vigore il più vicino al prezzo (il più alto per un long, il più basso per uno
  short). Nessuno spostamento quando il calcolato non è più vicino di quello in vigore.
- **Lavoro periodico del worker.** Un lavoro APScheduler a intervallo di un minuto, nella cartella `apscheduler/`
  come il controllo giornaliero, esegue un caso d'uso del contesto `flows` che per ogni flusso attivo con distanza o
  pareggio e ogni sua posizione aperta: legge il prezzo di mercato, aggiorna il miglior prezzo e il massimo profitto non
  realizzato raggiunti, calcola lo stop e, se è più vicino al prezzo, sostituisce l'ordine di stop attraverso la
  sostituzione esistente del contesto `orders`. I flussi senza impostazioni non leggono nessun prezzo.
- **Miglior prezzo registrato.** Una tabella nuova sotto RLS tiene per flusso e asset la posizione sorvegliata
  (istante d'apertura), il miglior prezzo e il massimo profitto raggiunti; si azzera quando la posizione si chiude o ne
  apre un'altra. Senza riga il miglior prezzo parte dal prezzo di mercato del primo controllo.
- **Nessuna sovrapposizione con il ciclo.** Il controllo di un flusso salta il turno se un ciclo dello stesso flusso è
  in corso (stesso segnale del ciclo in corso già usato tra i processi); riprova al minuto successivo.
- **Rifiuto dell'exchange.** Lo stop resta quello in vigore; il rifiuto si registra come quelli delle protezioni e il
  ciclo successivo lo riporta («stop BTC non aggiornato, <motivo>»).
- **Stop dell'agente.** Nel controllo del rischio, uno stop dell'agente più lontano dal prezzo dello stop calcolato
  dalla piattaforma si riporta allo stop calcolato, con la nota «stop <x> riportato a <y>: oltre lo stop che segue il
  prezzo», come il riporto entro il predefinito; uno stop dell'agente più vicino vale.
- La chiusura per lo stop spostato resta una chiusura per stop loss: nessuna causa nuova.

## Alternative scartate

- **Stop trailing nativo dell'exchange**: non disponibile in modo uniforme tra exchange e simulato, e non supporta
  attivazione e pareggio insieme.
- **Spostare lo stop solo nel ciclo**: lascia scoperto il tempo tra i cicli, che è il problema del requisito.

## Conseguenze

- Il worker fa una lettura di prezzo al minuto per ogni posizione sorvegliata, e nessuna per gli altri flussi.
