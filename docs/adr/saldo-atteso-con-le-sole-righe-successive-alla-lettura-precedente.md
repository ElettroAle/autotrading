# ADR saldo-atteso-con-le-sole-righe-successive-alla-lettura-precedente — Saldo atteso con le sole righe successive alla lettura precedente

- Stato: proposta (16 novembre 2026)
- Requisiti: Bug 506, Task 507; R1.6.2, R3.3.1
- Collegate: ADR allarme-di-riconciliazione-sul-saldo-del-conto (R3.3.1), ADR 0063 (registro delle operazioni),
  ADR 0076 (rilettura di un'ora del registro)

## Contesto e problema

`AccountReconciliation.of` calcola il saldo atteso come riferimento della lettura precedente più ciò che lo spiega
(`_explained` in `domain/flows/account_reconciliation.py`): le esecuzioni e il funding dei flussi che il registro ha
appena scritto, e i movimenti dichiarati dall'exchange dopo la lettura precedente. Solo i movimenti sono filtrati per
istante.

Il registro rilegge un'ora prima del cursore (ADR 0076) e scrive anche righe pubblicate in ritardo, con un istante
precedente alla lettura precedente: il funding si paga al cambio d'ora e i nodi API possono essere indietro. Il saldo
letto allora le comprendeva già ed è diventato il riferimento (`_next_reference`). La lettura successiva le conta
una seconda volta: ne esce uno scostamento piccolo, di segno qualsiasi, entro la soglia. Ogni scostamento entro la
soglia diverso da zero è un caso nuovo `BALANCE_CHANGE` (R1.6.2) notificato come movimento non attribuibile: su dev
arriva quasi a ogni riconciliazione.

## Fattori decisionali

- R3.3.1: il saldo atteso è il riferimento più esecuzioni, commissioni e funding dei flussi e i movimenti dichiarati
  dall'exchange **da allora**; ogni riga conta una volta.
- ADR 0063 e 0076: il registro scrive ogni riga una volta, anche in ritardo; la finestra di un'ora non si tocca.
- L'istante della lettura (`AccountActivity.read_at`) è il campo `time` dello stato di Hyperliquid: stesso orologio
  degli istanti di esecuzioni e funding, quindi confrontabili.
- Domain: la regola sta in `AccountReconciliation`, senza I/O.

## Opzioni considerate

1. `_explained` conta le esecuzioni (`executed_at`) e il funding (`paid_at`) dei flussi solo se successivi alla
   lettura precedente, come già fa con i movimenti (`moved_at`). Una riga con istante non successivo era già nel saldo
   letto allora, quindi nel riferimento.
2. Non azzerare il riferimento sul saldo letto entro la soglia (tenere l'atteso): scartata, lo scostamento si
   accumula e una differenza vera resterebbe per sempre.
3. Una tolleranza minima sullo scostamento: scartata come correzione di questo Bug, nasconde il doppio conteggio
   invece di toglierlo; se servisse è una scelta funzionale del proprietario.

## Esito della decisione

Opzione 1. Il registro e i totali dei flussi non cambiano: il filtro vale solo per il confronto del saldo.

Verifica: prova (scenario del Bug 506 sul caso d'uso `ReconcileAccountUseCase`; unit test di `AccountReconciliation`
con esecuzione e funding precedenti, uguali e successivi alla lettura precedente).

### Conseguenze

- Funding e esecuzioni pubblicati in ritardo non generano più variazioni del saldo non spiegate né notifiche.
- Una riga con istante identico alla lettura precedente si considera già nel saldo letto, come per i movimenti.
- Restano notificate le variazioni vere entro la soglia (R1.6.2): se la notifica dei piccoli scostamenti vada tolta
  o limitata è una domanda aperta al proprietario, fuori da questa decisione.
