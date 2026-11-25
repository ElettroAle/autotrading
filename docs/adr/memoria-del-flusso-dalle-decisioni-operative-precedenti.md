# ADR memoria-del-flusso-dalle-decisioni-operative-precedenti — Memoria del flusso: decisioni operative precedenti per asset, con esito, ampiezza configurabile

- Stato: superata da ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni (25 novembre 2026)
- Requisiti: US 363 R5.3.4 (Task 364, 728)
- Collegate: ADR 0094 (ciclo decisionale nel contesto `flows`), ADR 0104 (LangGraph), ADR system-prompt-del-flusso-come-modello-con-segnaposti, ADR 0070 (PnL della chiusura dal
  exchange), ADR 0116 (dashboard); `.claude/rules/context-flows.md`, `.claude/rules/context-agent.md`,
  `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-fastapi.md`, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.3.4 (RF-28.09) vuole che l'agente riceva nel contesto le proprie decisioni precedenti sullo stesso asset con
l'esito ottenuto, se la memoria del flusso è attiva, e che l'utente veda la memoria sul flusso (ciò che l'agente
riceverà) e nel ciclo (ciò che l'agente ha ricevuto). Servono: che cosa entra nella memoria, quanto, da dove si legge
l'esito, dove si registra e come si mostra.

## Fattori decisionali

- Decisioni del proprietario (24 novembre 2026, in chat): entrano solo le decisioni operative; numero e finestra sono
  impostazioni del flusso, con predefiniti 10 decisioni per asset e 30 giorni (modifica il testo del requisito, che le
  voleva fisse; il requisito sulla board è stato aggiornato).
- `CLAUDE.md`: regole di business nel domain; il caso d'uso orchestra le porte; nessuna duplicazione; SOLID e Clean
  Code; dati del tenant con RLS dentro l'adapter `sqlalchemy/`.
- Il comitato (gestore) e il replay non esistono ancora: la memoria nasce per l'agente unico con una regola sull'istante
  che il replay potrà usare senza cambiarla.

## Decisione

### Impostazione del flusso

- Nuovo value object di dominio `FlowMemory` in `domain/flows/`: `active: bool`, `decisions: int`, `days: int`.
  Predefinito non attiva, 10 decisioni, 30 giorni. Limiti validati nel domain: decisioni da 1 a 50, giorni da 1 a 365;
  fuori dai limiti un errore di dominio 422 con il motivo. Fa parte della versione del flusso come le altre
  impostazioni: crearlo, modificarlo, duplicarlo e importare la strategia la portano; cambiarla crea una versione.
- API: campo `memory` (`active`, `decisions`, `days`) nella creazione, nella modifica e nella lettura del flusso,
  facoltativo con i predefiniti. Dashboard: sezione «Memoria» nel modulo del flusso subito dopo il modello, perché
  regola ciò che il modello riceve (interruttore, decisioni, giorni, questi ultimi abilitati solo con la memoria
  attiva; decisione del proprietario, 25 novembre 2026).

### Contenuto della memoria

- Una voce di memoria è una decisione operativa precedente del flusso stesso su quell'asset: apri, chiudi, inverti,
  modifica delle protezioni. Le decisioni di non agire non entrano. Per ogni voce: istante del ciclo, azione (con la
  direzione per apri e inverti), prezzo dell'asset al ciclo, motivazione sintetica della decisione ed esito.
- Esito: PnL della posizione aperta da quella decisione (`closed_positions.opening_cycle`, o la posizione aperta del
  flusso nata in quel ciclo). Realizzato se chiusa, non realizzato al prezzo corrente se aperta; per chiudi il PnL
  realizzato della chiusura; nessun esito se la posizione non è nata (ordine rifiutato) o se la decisione è una modifica
  delle protezioni.
- Selezione: per ogni asset del flusso, le ultime `decisions` voci con istante anteriore all'istante del ciclo e non più
  vecchie di `days` giorni, dalla più recente. La regola (filtro operativo, ordine, limiti, istante) sta nel domain, in
  un tipo che riceve le decisioni e gli esiti letti e restituisce la memoria per asset.
- Lettura: nuova porta del contesto `flows` per le decisioni precedenti con il loro esito, realizzata dall'adapter
  `sqlalchemy/` su `cycle_decisions`, `closed_positions` e le posizioni aperte del flusso, legata al tenant (RLS).

### Uso nel ciclo

- Decisione del proprietario (24 novembre 2026, in chat): la memoria entra come **segnaposto del system prompt**,
  secondo ADR system-prompt-del-flusso-come-modello-con-segnaposti. Un nuovo membro del registro `PromptPlaceholder`
  del domain `flows` (nome e descrizione dichiarati una volta sola nel registro) è sostituito con la memoria, un
  blocco per asset in testo italiano compatto. Il testo predefinito del system prompt lo contiene in una sezione
  propria; un system prompt personalizzato lo usa se l'utente lo scrive. Con la memoria non attiva, o senza voci, il
  segnaposto si sostituisce con un testo vuoto, e il passo del ciclo non legge le decisioni.
- La memoria data all'agente si registra con il ciclo, come i documenti dei passi, ed è restituita dal dettaglio del
  ciclo nell'API e mostrata nella dashboard nel dettaglio del ciclo.

### Consultazione

- Nuova lettura dell'API `GET /flows/{flow_id}/memory`: la memoria che l'agente riceverebbe se il ciclo partisse ora,
  per asset; con la memoria non attiva risponde con `active: false` e nessuna voce. La memoria è un dettaglio da
  aprire su richiesta, non un dato della panoramica (decisione del proprietario, 25 novembre 2026): la dashboard la
  offre solo con la memoria attiva, nella scheda «Decisioni» della pagina del flusso, in una sezione chiusa
  («Memoria dell'agente», la sezione apribile condivisa con il dettaglio del ciclo, ADR 0129) con i componenti
  esistenti di tabella.

## Alternative scartate

- **Numero e finestra fissi** (testo iniziale del requisito): il proprietario li vuole configurabili.
- **Anche le decisioni di non agire**: con cicli di pochi minuti riempirebbero la memoria di ripetizioni.
- **Memoria come sezione del contesto fuori dal system prompt**: il proprietario la vuole come segnaposto del system
  prompt, visibile e spostabile nel modello del prompt come le altre parti.
- **Memoria come fonte del ciclo (adapter di fonte)**: è un dato del flusso stesso, non un sistema esterno; una fonte
  la renderebbe disattivabile per errore e la mescolerebbe ai pesi delle fonti.
- **Memoria calcolata dal modello su tutto lo storico**: costo in token non limitato.

## Conseguenze

- Una colonna o un campo in più nella versione del flusso (migrazione con predefinito non attiva, 10, 30).
- Il contesto dell'agente cresce di circa 50-80 token per voce con la memoria attiva.
- Il gestore del comitato e il replay useranno la stessa memoria e la stessa regola sull'istante.
