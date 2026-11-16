# ADR capitale-libero-al-netto-del-valore-dei-flussi — Capitale libero al netto del valore dei flussi

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.4.1 (464), Task T3.4.1.3 (505); R1.1.1 (65) e R1.1.7 (78) aggiornati
- Sostituisce: la definizione del capitale libero di ADR 0031 («saldo letto dall'exchange meno le allocazioni»), di
  ADR 0053 (capitale disponibile all'ammissione di un aumento) e di ADR 0124 (capitale dei flussi né archiviati né in
  bozza); il resto di quelle ADR resta valido
- Collegate: ADR 0063 (registro delle esecuzioni e totali del flusso), ADR 0078 (fondi del flusso), ADR 0142,
  ADR saldo-dalla-modalita-del-conto-hyperliquid

## Contesto e problema

Oggi il capitale libero di un conto è il saldo letto dall'exchange meno la somma dei capitali allocati ai suoi flussi
(`domain/flows/free_capital.py`). Il saldo contiene già i guadagni e le perdite dei flussi, quindi il profitto di un
flusso conta due volte: nei fondi del flusso (`FlowState.funds`) e nel capitale libero, dove un altro flusso può
riceverlo. R3.4.1 vuole invece che il profitto resti del flusso finché l'utente non lo incassa, e che solo l'incasso
lo porti nel capitale libero: con la definizione attuale lo scenario «Incasso al capitale allocato attuale» non può
passare.

## Fattori decisionali

- Decisione del proprietario (16/11/2026, domanda sul capitale di F3.4): il capitale libero diventa saldo meno i fondi
  dei flussi (capitale allocato + PnL netto − incassi); il profitto resta del flusso finché non lo si incassa;
  R3.4.1-R3.4.3 restano come sono.
- ADR saldo-dalla-modalita-del-conto-hyperliquid: in ogni modalità del conto il saldo include il PnL non realizzato
  delle posizioni perps.
- R1.6.1 e ADR 0062: lo stato attribuito al flusso (`FlowState`) è l'unica misura del suo denaro, la stessa che
  l'utente consulta.
- CLAUDE.md: il calcolo è una regola di business e sta nel domain; nessuna copia provvisoria del calcolo.

## Opzioni considerate

1. Capitale libero = saldo − somma dei **valori complessivi** (`FlowState.total_value`) dei flussi del conto che
   tengono il conto (`status.holds_account`), con i fondi del flusso al netto dei profitti incassati. Il PnL netto
   comprende anche il non realizzato perché il saldo lo comprende: altrimenti il guadagno di una posizione aperta
   sarebbe capitale libero e un altro flusso potrebbe impegnarlo.
2. Capitale libero = saldo − (capitale allocato + PnL realizzato netto − incassi), senza il non realizzato: scartata,
   perché il guadagno o la perdita aperta di un flusso cambierebbe il capitale libero degli altri a ogni movimento di
   prezzo.
3. Lasciare la definizione e riscrivere R3.4.1: scartata dal proprietario.

## Esito della decisione

Opzione 1.

- **Profitto incassato**: `FlowTotals` (ADR 0063) non cambia. I profitti incassati di un flusso sono la somma della
  parte di profitto dei suoi incassi, registrata con la variazione di capitale dell'incasso (ADR
  incasso-dei-profitti). `FlowState` riceve `cashed_profit` e i fondi diventano capitale allocato + PnL realizzato −
  commissioni + funding − profitti incassati; liquidità disponibile, valore complessivo e limiti percentuali (ADR
  0078) ne seguono senza altre modifiche. Il PnL del flusso in valuta non toglie gli incassi (R3.4.3).
- **Calcolo**: `FreeCapital.of(balance, currency, states)` toglie dal saldo la somma dei `total_value` degli stati;
  `allocated_capital_of_account` resta solo dove serve il capitale allocato (elenco dei conti, ADR 0126).
- **Lettura**: un solo passo applicativo legge lo stato del conto (saldo e posizioni, in una lettura), i totali del
  registro dei flussi del conto e i profitti incassati, e attribuisce uno stato a ogni flusso che tiene il conto. Lo
  usano `ReadFreeCapitalUseCase` e ogni caso d'uso che oggi chiama `FreeCapital.of_account` (creazione, assegnazione
  della bozza, avvio di un flusso fermo, aumento del capitale), che non calcolano più il capitale libero da sé.
  Restano le esclusioni di oggi: il flusso stesso al suo avvio (ADR 0142), i flussi archiviati e quelli in bozza.
- **Aumento** (R1.1.7): resta ammesso se l'aumento non supera il capitale libero letto ora.

Verifica: prova (scenario «Il valore degli altri flussi non è capitale libero» di R1.1.1, scenari di R1.1.7 e di
R3.4.1; unit test di `FreeCapital` e `FlowState`).

### Conseguenze

- Guadagni e perdite di un flusso non spostano più il capitale libero del conto. Una perdita resta del flusso; un
  guadagno diventa capitale libero solo con l'incasso o con l'archiviazione del flusso.
- Il capitale libero richiede le posizioni del conto oltre al saldo. La lettura dello stato del conto c'è già: si
  aggiungono i totali del registro dei flussi del conto.
- Un flusso fermo con un profitto lo tiene finché non lo si incassa o lo si archivia.
