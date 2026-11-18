# ADR avvisi-nel-contesto-delle-notifiche — Modello e ciclo di vita degli avvisi

- Stato: proposta (18 novembre 2026)
- Requisiti: R6.2.3, Task 607; R1.6.2, R1.2.4, R3.3.1
- Collegate: ADR destinazioni-delle-notifiche-nella-dashboard, ADR variazioni-sotto-soglia-senza-notifica, ADR 0089
  (nessun ponte tra contesti), ADR 0092 (notifiche come passi espliciti dei casi d'uso)
- Verifica: prova

## Contesto e problema

R6.2.3 chiede un elenco unico di ciò che chiede un intervento, da più fonti (riconciliazione, pausa automatica dei
flussi, non attribuibili), con gravità, stato e risorsa interessata. Oggi esistono solo le notifiche (racconto) e gli
allarmi di riconciliazione del contesto `flows`.

## Fattori decisionali

- CLAUDE.md: un contesto nuovo nasce solo con decisione del proprietario; l'avviso nasce insieme alla sua notifica
  (R6.2.3), quindi sta nel contesto `notifications`, che già riceve ogni evento.
- Nessun ponte: `flows` dichiara le sue porte per risolvere gli avvisi, l'adapter SQLAlchemy le realizza.
- Decisioni del proprietario (17/11/2026): stati aperto e risolto; gravità critica e attenzione.

## Decisione

- Domain `domain/notifications/alert.py`: `Alert` (id `AlertId`, `AlertKind`, risorsa `AlertResource` con genere
  `ACCOUNT`, `FLOW` o `KEY`, id e nome, chiave della causa, valori letti, aperto il, risolto il). `AlertKind`:
  `RECONCILIATION_ALARM` (critica, si risolve con la conferma), `FLOW_PAUSED` (critica, con ripresa, stop o
  archiviazione), `UNATTRIBUTABLE_POSITION` (attenzione, quando la posizione sparisce), `UNATTRIBUTABLE_FILL`
  (attenzione, a mano). Gravità e risoluzione a mano sono proprietà del genere, nel domain; la risoluzione a mano di un
  genere con risoluzione automatica solleva `AlertNotResolvableByHandError` (409). La chiave della causa (per esempio
  conto e asset) rende l'apertura idempotente finché l'avviso è aperto.
- Application `notifications`: `AlertRepositoryPort` (apri se non aperto, risolvi per chiave della causa, risolvi per
  id, elenco filtrato per keyset, conteggio degli aperti, dettaglio). I casi d'uso di notifica dei quattro eventi
  aprono l'avviso prima di inviare la notifica (passo esplicito, ADR 0092). Ogni apertura cancella gli avvisi del
  tenant risolti da oltre 90 giorni.
- Risoluzione automatica: `flows` dichiara `AlertResolutionPort` in `application/flows/ports.py` e la chiama dalla
  conferma della riconciliazione (allarme), dai casi d'uso di ripresa, stop e archiviazione (pausa) e da
  `ReconcileAccountUseCase` quando una posizione non attribuibile non c'è più; la realizza l'adapter degli avvisi
  nella cartella `sqlalchemy/`.
- Persistenza: tabella `alerts` con RLS del tenant, indice unico parziale sulla chiave della causa per gli aperti;
  migrazione Alembic.
- La chiave in scadenza (R6.2.2) diventa un genere quando R6.2.2 si sviluppa.
- Prove: unit test del domain e dei casi d'uso con finti; integrazione del repository (idempotenza, RLS, pulizia a 90
  giorni); scenari R6.2.3 sui casi d'uso.

## Alternative scartate

- Contesto `alerts` nuovo: richiede la decisione del proprietario; il contesto `notifications` già riceve ogni evento.
- Avvisi ricavati a ogni lettura dagli stati delle fonti: nessuno storico dei risolti e logica duplicata per fonte.

## Conseguenze

- Una fonte nuova di avvisi aggiunge un genere e il punto in cui si risolve.
