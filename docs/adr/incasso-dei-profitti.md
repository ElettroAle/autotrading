# ADR incasso-dei-profitti — Comando di incasso dei profitti di un flusso

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.4.1 (464), Task T3.4.1.1 (487)
- Collegate: ADR capitale-libero-al-netto-del-valore-dei-flussi, ADR 0053 (variazione del capitale e cronologia),
  ADR 0055 (stop e chiusura delle posizioni), ADR 0063 (registro delle esecuzioni), ADR
  chiusura-di-emergenza-per-ambito (F3.2), ADR permanenza-decisa-dall-errore-base

## Contesto e problema

R3.4.1 chiede un comando che chiuda le posizioni di un flusso e liberi la differenza tra il suo valore e il nuovo
capitale allocato, senza cambiarne lo stato. Va deciso dove si decide, come si misura il valore dopo le chiusure e
come si registra l'incasso perché il capitale libero lo veda (ADR capitale-libero-al-netto-del-valore-dei-flussi).

## Fattori decisionali

- Decisione del proprietario (16/11/2026): il profitto resta del flusso finché non lo si incassa; l'incasso lo porta
  nel capitale libero.
- CLAUDE.md: un caso d'uso per modulo, che orchestra le porte; errori tipizzati del progetto che dichiarano la propria
  risposta; nessun duplicato provvisorio (la chiusura delle posizioni di un flusso esiste già nello stop).
- ADR 0063: i totali del flusso vengono dalle esecuzioni dichiarate dall'exchange, registrate nel registro.
- R3.4.2: l'incasso è una variazione di capitale con motivo «incasso».

## Opzioni considerate

1. `CashOutProfitsUseCase` nel contesto `flows`: legge lo stato del flusso, valida, chiude le posizioni con la
   chiusura condivisa, registra le esecuzioni, rilegge lo stato e scrive l'incasso come variazione di capitale.
2. Ridurre il capitale allocato e lasciare il profitto nel saldo: scartata, perché con la nuova definizione del
   capitale libero il profitto resterebbe del flusso.

## Esito della decisione

Opzione 1, in passi nominati:

1. **Stato e controlli**: legge lo stato attribuito (`ReadFlowStateUseCase`). Se il valore complessivo non supera il
   capitale allocato solleva `FlowWithoutProfitsError` («alfa non ha profitti da incassare», 409). Un capitale
   indicato fuori da (0, valore complessivo) solleva `CashOutCapitalOutOfRangeError` («il capitale indicato è
   maggiore di 0 e minore del valore del flusso, 618 USDC», 400). Nessuna chiusura avviene prima dei controlli.
2. **Chiusure**: chiude tutte le posizioni del flusso con la chiusura estratta dallo stop (`CloseFlowPositionsUseCase`,
   come decide l'ADR chiusura-di-emergenza-per-ambito di F3.2: il primo dei due rami che arriva su `main` la estrae,
   l'altro la riusa), con il nuovo motivo `CloseReason.CASH_OUT = "incasso"`. Il flusso non cambia stato.
3. **Esito parziale**: se una chiusura fallisce non si registra nulla; la risposta (200) riporta le posizioni non
   chiuse con il motivo dell'exchange, come lo stop (`StopOutcome`).
4. **Valore dopo le chiusure**: registra le esecuzioni del conto (`RecordAccountExecutionsUseCase`, ADR 0063) e
   rilegge lo stato: il valore è quello reale, commissioni di chiusura comprese (620 diventa 618).
5. **Registrazione**: il nuovo capitale è quello indicato, o l'attuale. In una sola transazione della porta del
   flusso si scrivono la nuova versione della configurazione, se il capitale cambia (come in R1.1.7), e la variazione
   di capitale con motivo `incasso`, importo liberato (valore − nuovo capitale), capitale prima e dopo, valore del
   flusso prima e profitto incassato (valore − capitale allocato prima). Il capitale libero sale dell'importo
   liberato. Anche aumento e riduzione (R1.1.7) registrano da ora motivo, importo e valore del flusso prima, che
   servono al rendimento composto (ADR rendimento-composto-tra-le-variazioni-di-capitale).
6. **Rotta**: `POST /flows/{flow_id}/cash-out` con corpo facoltativo `{capital}`; la risposta porta importo liberato,
   nuovo capitale e posizioni non chiuse.

Verifica: prova (scenari di R3.4.1 sui casi d'uso con adapter finti, unit test di dominio e del caso d'uso, test di
integrazione dell'adapter sqlalchemy per la variazione con motivo e profitto incassato).

### Conseguenze

- Stop, chiusura di emergenza e incasso condividono un solo modo di chiudere le posizioni di un flusso.
- La variazione di capitale guadagna motivo, importo, valore prima e profitto incassato: serve una migrazione, il cui
  numero si sceglie all'integrazione per non collidere con F3.2 e F3.3. Le variazioni registrate prima hanno il motivo
  «aumento» o «riduzione» dedotto dal segno e nessun valore prima.
