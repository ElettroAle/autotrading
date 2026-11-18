# ADR inversione-in-due-passi-nel-ciclo — Azione «inverti»: chiusura e apertura opposta nello stesso ciclo, in due passi

- Stato: proposta (18 novembre 2026)
- Requisiti: US 547 R1.4.10, Task 548; R1.4.4, R1.5.3, R1.4.8, R3.1.2, R1.7.2
- Collegate: ADR 0094 (ciclo in `flows`), ADR 0104 e 0105 (grafo LangGraph del ciclo), ADR 0065 (ordine del controllo
  del rischio), ADR system-prompt-del-flusso-come-modello-con-segnaposti, ADR icone-condivise-di-azioni-e-direzioni;
  `.claude/rules/context-agent.md`, `.claude/rules/context-flows.md`
- Verifica: prova

## Contesto e problema

Le azioni dell'agente sono `apri`, `chiudi`, `mantieni`, `aggiorna` (`domain/agent/decision.py`, `TradeAction`). Per
cambiare direzione su un asset il flusso chiude in un ciclo e riapre nel successivo, restando fuori dal mercato per un
intervallo. R1.4.10 chiede l'azione «inverti»: chiusura totale e apertura opposta nello stesso ciclo, con l'apertura
controllata sui soldi e sulla liquidità del flusso dopo la chiusura eseguita. Oggi il grafo del ciclo controlla il
rischio una volta (`risk_filter`) e manda tutti gli ordini in una sola esecuzione (`execute`).

## Fattori decisionali

- R1.4.10 (proprietario): direzione sempre opposta a quella aperta, campo direzione ignorato; quota, leva, obiettivo,
  stop, invalidazione e confidenza come un'apertura; prima la chiusura; l'apertura controllata come ogni apertura sui
  soldi dopo la chiusura; apertura bloccata non annulla la chiusura; chiusura non eseguita, apertura non inviata;
  storico col motivo «inversione».
- Regole di `flows`: ordine del controllo leva, esposizione, coerenza, importo minimo (ADR 0065); il registro si scrive
  solo con `RecordAccountExecutionsUseCase` dalla riconciliazione del conto; gli ordini passano da `orders`.
- Il ciclo è il grafo di `cycle_graph.py`: un passo nuovo è un nodo che chiama la porta del suo passo.
- `agent` dichiara le azioni ammesse (`ListAgentActionsUseCase`) che il system prompt predefinito nomina.

## Decisione

- **Agent (domain)**: `TradeAction.REVERSE = "inverti"`; `AgentResponse` legge «inverti» con i campi di un'apertura,
  il campo direzione facoltativo e ignorato; `Decision.intent_with` riceve una funzione `reversing` con gli stessi
  argomenti dell'apertura tranne la direzione. Il formato rigido delle decisioni (`DECISIONS_FORMAT`) e le azioni
  ammesse derivano dallo stesso enum; il system prompt predefinito spiega «inverti».
- **Controllo del rischio, primo passo** (`risk_filter`): un `ReverseIntent` su un asset senza posizione aperta del
  flusso è bloccato per coerenza con il motivo «nessuna posizione da invertire» (R1.5.3); altrimenti diventa una
  chiusura approvata col motivo `CloseReason.REVERSAL = "inversione"` più un'apertura in attesa, con la direzione
  opposta a quella della posizione aperta.
- **Esecuzione, primo passo** (`execute`): invariata; le chiusure delle inversioni partono con gli altri ordini.
- **Nodo nuovo `reverse`** tra `execute` e `update_ledger`, solo se il ciclo ha aperture in attesa, con un caso d'uso
  `ReverseCyclePositionsUseCase` di `flows`:
  1. riconcilia il conto (`RecordAccountExecutionsUseCase`), così soldi e liquidità del flusso contano il risultato
     della chiusura;
  2. per ogni apertura in attesa, se la posizione del flusso è ancora aperta (chiusura non eseguita) l'apertura non si
     invia e si registra bloccata col motivo «chiusura non eseguita»;
  3. le altre si controllano come aperture (`RiskCheck`, stesso ordine e stessi limiti, aperture sospese e confidenza
     minima comprese) sullo stato riletto e si inviano con `SendCycleOrdersUseCase`, con stop e obiettivo come R3.1.2.
- **Registro del ciclo**: la decisione «inverti» registra due esiti, quello della chiusura e quello dell'apertura;
  la posizione chiusa entra nello storico col motivo «inversione».
- **Dashboard**: la vista delle decisioni mostra «inverti» con `ActionLabel` (icona condivisa nuova in
  `components/ui/icons`) e i due esiti.
- **Specifiche**: nuovo `.feature` R1.4.10; R1.4.4 (azioni ammesse) e R1.5.3 (inverti senza posizione è incoerente)
  si aggiornano nello stesso lavoro.

## Alternative scartate

- Un solo controllo del rischio prima di ogni ordine: l'apertura non vedrebbe i soldi dopo la chiusura (R1.4.10).
- Un ordine «reduce and flip» dell'exchange: la chiusura e l'apertura non avrebbero esiti separati e la piattaforma
  non controllerebbe l'apertura sullo stato riletto.

## Conseguenze

- Un ciclo con un'inversione fa due esecuzioni verso l'exchange e una riconciliazione in più.
