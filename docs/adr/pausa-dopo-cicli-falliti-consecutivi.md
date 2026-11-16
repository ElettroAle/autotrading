# ADR pausa-dopo-cicli-falliti-consecutivi — Pausa dopo cicli falliti consecutivi contati sui cicli registrati

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.2.4 (461), Task T3.2.4.1 (484)
- Collegate: ADR 0051 (porta al minimo nella configurazione), ADR 0082 (regole del ciclo nell'esagono), ADR
  permanenza-decisa-dall-errore-base

## Contesto e problema

Un ciclo che fallisce per un errore non permanente lascia il flusso attivo: il ciclo successivo riprova e, se
fallisce ancora, notifica ancora (R1.2.4). Il proprietario vuole un massimo facoltativo di cicli falliti di fila,
oltre il quale il flusso va in pausa da solo con il motivo e la notifica di pausa automatica. Il conteggio si azzera
con un ciclo riuscito e con la ripresa del flusso. Gli errori permanenti mettono già in pausa al primo ciclo.

## Fattori decisionali

- R3.2.4 e decisione del proprietario sull'intervista di E3: pausa solo se il massimo è impostato.
- R1.1.3: ogni modifica del massimo crea una versione della configurazione.
- Il ciclo registra già ogni esito (completato, fallito, saltato) e `flows.cycle_anchor` si aggiorna a ogni
  passaggio in "attivo", cioè anche a ogni ripresa.
- Bug 441: ogni parte nuova della configurazione compare nel confronto delle versioni
  (`configuration_difference.py` e `dashboard/src/features/flow-versions/utils/configuration-rows.ts`).
- Componenti riusabili dove possibile (decisione del proprietario, 16/11/2026): il campo del modulo usa i campi
  condivisi di `src/components/ui/form`.

## Opzioni considerate

1. **Conteggio letto dai cicli registrati.** Una porta `ConsecutiveFailuresPort` in `application/flows/ports.py`
   conta i cicli falliti del flusso registrati dopo l'ultimo ciclo completato e dopo l'ancora dei cicli (la
   ripresa); i cicli saltati non contano né azzerano. La realizza l'adapter `sqlalchemy` dei cicli.
2. Contatore salvato sul flusso, incrementato a ogni fallimento e azzerato da successi e ripresa: scartata, duplica
   un dato già nei cicli e richiede di azzerarlo in più punti (ciclo riuscito, ripresa).

## Esito della decisione

Opzione 1.

- Domain: `FlowConfiguration.max_consecutive_failures: int | None = None`, validato da 1 a 100 con un errore
  tipizzato ("il massimo di cicli falliti consecutivi va da 1 a 100", 400), voce
  `FlowSetting.MAX_CONSECUTIVE_FAILURES = "max_consecutive_failures"`; parte "cicli falliti consecutivi massimi"
  nel confronto delle versioni (`nessuno` se assente).
- Persistenza: chiave facoltativa `max_consecutive_failures` nel documento JSON della versione (`NotRequired`,
  assente = nessun massimo): nessuna migrazione, come `bring_to_minimum` (ADR 0051).
- Casi d'uso: il campo in creazione, modifica (`None` = invariato, come gli altri limiti), importazione ed
  esportazione della strategia.
- Ciclo: un caso d'uso `PauseAfterConsecutiveFailuresUseCase` (porte: flussi, `ConsecutiveFailuresPort` e la porta
  di pausa già usata per gli errori permanenti) riceve id del flusso ed errore; se la configurazione in vigore ha il
  massimo e il conteggio, dopo la registrazione del ciclo fallito, lo raggiunge, chiede la pausa con
  `PauseAffectedFlowsCommand(flow_id, "<N> cicli falliti consecutivi: <errore>")`. `RunCycleUseCase._failed` lo
  chiama, attraverso una porta nuova di `CycleGuards`, solo per gli errori non permanenti, dopo la notifica del
  ciclo fallito. La notifica di pausa è quella esistente ("alfa: in pausa, <motivo>"); nessun ordine si invia, le
  posizioni e i loro ordini di protezione restano.
- API e dashboard: campo facoltativo `max_consecutive_failures` nelle richieste e risposte dei flussi, nel documento
  della strategia, nel client OpenAPI rigenerato, nel modulo del flusso (intero facoltativo) e nelle righe del
  confronto delle versioni.

Verifica: prova (scenari di R3.2.4 sul caso d'uso del ciclo con adapter finti, unit test di domain e casi d'uso,
test di integrazione del conteggio sull'adapter `sqlalchemy`, test del modulo nella dashboard).

### Conseguenze

- Il conteggio segue da sé ogni esito registrato; la ripresa azzera senza scritture aggiuntive.
- Un ciclo saltato perché il precedente era ancora in corso non interrompe la serie dei falliti.
