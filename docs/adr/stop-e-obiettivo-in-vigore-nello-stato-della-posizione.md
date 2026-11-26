# ADR stop-e-obiettivo-in-vigore-nello-stato-della-posizione — Stop e obiettivo in vigore sull'exchange nello stato della posizione

- Stato: accettata (26 novembre 2026)
- Requisiti: US 758 R5.5.3 (Task 759)
- Collegate: ADR 0094 (ciclo decisionale nel contesto `flows`), ADR aggiornamento-del-piano-di-uscita-di-una-posizione-aperta,
  ADR protezioni-ritentate-nel-ciclo, ADR 0007 (credenziali decifrabili solo dal worker); `.claude/rules/context-flows.md`,
  `.claude/rules/context-orders.md`, `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

Lo stato di un flusso riporta per ogni posizione aperta il piano di uscita dell'agente. Quando lo stop o l'obiettivo
vengono dai predefiniti del flusso, o lo stop dell'agente è stato riportato entro il predefinito, il piano dell'agente
non li contiene o ne contiene un altro valore: agente, API, strumenti MCP e dashboard leggono «stop: nessuno» mentre
sull'exchange c'è uno stop. Le protezioni che la piattaforma mette o sostituisce sono già registrate con il loro prezzo
(`flow_protections`, porta `FlowProtectionLevelsPort`); le posizioni aperte prima che la piattaforma registrasse le
protezioni possono non averne.

## Fattori decisionali

- Requisito R5.5.3 del proprietario: lo stato riporta il livello inviato all'exchange qualunque sia l'origine; la fonte
  è il livello registrato a ogni posizionamento o sostituzione; per una posizione senza livello registrato la
  piattaforma lo legge una volta dagli ordini sull'exchange e lo registra; vale per agente, API, MCP e dashboard;
  senza ordine di take profit l'obiettivo è vuoto; l'agente lo riceve sempre, senza opzione.
- Ordine del proprietario per il perimetro F5.5 (26 novembre 2026): nessuna impostazione nuova qui, nessuna versione
  nuova della configurazione dei flussi esistenti.
- `CLAUDE.md`: un solo punto per la stessa conoscenza; niente ponti tra contesti (il contesto che usa un dato dichiara
  la sua porta); le credenziali dei conti le legge solo il worker (ADR 0007).

## Decisione

- **Una sola lettura.** `ReadFlowStateUseCase`, che già serve agente (worker), API, strumenti MCP e dashboard, riceve
  anche `FlowProtectionLevelsPort` e compone il piano in vigore di ogni posizione aperta: stop e obiettivo sono i
  livelli registrati delle protezioni in vigore; l'invalidazione resta quella del piano dell'agente. Senza protezione
  di un tipo registrata, quel livello è vuoto (una posizione senza take profit ha obiettivo vuoto). La regola di
  composizione è del domain, in un solo punto (`ExitPlan` con i livelli in vigore).
- **Posizioni senza livello registrato.** All'inizio del ciclo, prima che lo stato per l'agente sia letto, il worker
  registra le protezioni in attesa sull'exchange di ogni posizione del flusso che non ne ha di registrate: un caso
  d'uso del contesto `orders` legge le protezioni attive con `ProtectionExchangePort.active` e le registra con
  `ProtectionRepositoryPort`, come quelle che la piattaforma mette. La lettura delle protezioni attive di una posizione
  è condivisa con `ProtectOpenPositionsUseCase`, non ripetuta. Una posizione con protezioni già registrate non legge
  l'exchange. L'API non legge l'exchange: mostra ciò che il worker ha registrato.
- **Dashboard.** La vista della posizione mostra stop e obiettivo che l'API restituisce; nessun calcolo nella
  dashboard (ADR 0116).
- Nessuna migrazione: la tabella delle protezioni registrate esiste già.

## Alternative scartate

- **Calcolare lo stop dal predefinito del flusso nella lettura dello stato**: ripete la regola del posizionamento e
  sbaglia quando lo stop è stato riportato o rifiutato dall'exchange.
- **Leggere l'exchange a ogni lettura dello stato**: l'API non decifra le credenziali (ADR 0007) e moltiplica le
  chiamate.

## Conseguenze

- Lo stato mostra il livello che protegge davvero la posizione; il piano dell'agente resta registrato per
  l'invalidazione e per gli aggiornamenti del piano.
- Una posizione aperta prima del requisito mostra lo stop dal ciclo in cui il worker ne registra le protezioni.
