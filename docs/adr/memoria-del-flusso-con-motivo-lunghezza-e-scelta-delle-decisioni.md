# ADR memoria-del-flusso-con-motivo-lunghezza-e-scelta-delle-decisioni — Memoria del flusso: motivo in una frase, lunghezza configurabile, chiusure con causa e durata, scelta delle decisioni ricordate

- Stato: proposta (25 novembre 2026)
- Requisiti: US 742 R5.3.5 (Task 743, 744, 745)
- Sostituisce: ADR memoria-del-flusso-dalle-decisioni-operative-precedenti (proposta)
- Collegate: ADR 0094 (ciclo decisionale nel contesto `flows`), ADR system-prompt-del-flusso-come-modello-con-segnaposti,
  ADR decisioni-del-ciclo-registrate-per-asset, ADR 0070 (PnL della chiusura dal exchange), ADR 0129 (sezioni
  apribili), ADR server-mcp-in-un-container-proprio-con-accesso-entra; `.claude/rules/context-flows.md`,
  `.claude/rules/context-agent.md`, `.claude/rules/tech-sqlalchemy.md`, `.claude/rules/tech-fastapi.md`,
  `.claude/rules/tech-mcp.md`, `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.3.4 ha dato all'agente le sue decisioni operative precedenti per asset, con i primi 160 caratteri del ragionamento:
una lunghezza scelta dallo sviluppo. I ragionamenti cominciano dal contesto di mercato, quindi in memoria finisce il
contesto e non il motivo; le chiusure per stop loss o take profit non dicono perché e dopo quanto la posizione si è
chiusa; gli aggiornamenti delle protezioni occupano posti senza dare informazioni. R5.3.5 chiede che l'agente
riconosca una tesi che sta fallendo.

## Fattori decisionali

- Requisito R5.3.5 del proprietario (25 novembre 2026): motivo in una frase, lunghezza configurabile (160 predefinita,
  intero positivo o illimitata), causa e durata delle chiusure, impostazione «tutte le decisioni» spenta di base; le
  nuove impostazioni si gestiscono come le altre della memoria.
- Decisioni del proprietario già scritte e confermate: la memoria è un segnaposto del system prompt, vuoto con la
  memoria non attiva; nel modulo del flusso la sezione «Memoria» sta dopo il modello; nella pagina del flusso la
  memoria si consulta su richiesta nella scheda «Decisioni» (25 novembre 2026).
- `CLAUDE.md`: regole di business nel domain; nessuna duplicazione; SOLID e Clean Code; dati del tenant con RLS dentro
  l'adapter `sqlalchemy/`; ogni operazione sui flussi dell'API anche come strumento MCP.

## Decisione

Resta tutto ciò che l'ADR sostituita decideva, salvo quanto segue.

### Motivo della decisione (Task 743)

- La risposta del modello ha, per ogni decisione (apri, chiudi, inverti, aggiorna, mantieni), il campo `motivo`: una
  frase separata dal `ragionamento`. Il formato della risposta nel system prompt predefinito lo descrive: per apri e
  inverti la tesi, per chiudi il fatto o il livello che ha causato la chiusura, per aggiorna cosa cambia e perché, per
  mantieni cosa l'agente aspetta.
- Il domain dell'agente legge `motivo` come testo facoltativo: una risposta senza motivo resta leggibile e la decisione
  vale (un system prompt personalizzato scritto prima di R5.3.5 non lo chiede). Scelta presa senza una regola scritta:
  rendere il campo obbligatorio farebbe fallire i cicli dei flussi con un prompt personalizzato.
- Il ciclo registra con la decisione il motivo e, per apri e inverti, l'invalidazione del piano di uscita dichiarata:
  due colonne nuove facoltative di `cycle_decisions` (migrazione), lette da `RecordedDecision`.
- In memoria entrano il motivo e, per apri e inverti, l'invalidazione; il ragionamento completo resta nel registro del
  ciclo e non entra. Una decisione senza motivo (registrata prima, o di un modello che non l'ha dato) entra con
  l'inizio del suo ragionamento, come oggi. La scelta del testo sta nel domain, in un solo punto.

### Impostazioni della memoria (Task 744)

- `FlowMemory` ha due parti nuove: `text_length` (intero positivo, oppure nessun limite per «illimitata»; predefinito
  160) e `all_decisions` (predefinito spenta). Una lunghezza zero o negativa è un errore di dominio 422 con il motivo.
  Fanno parte della versione del flusso come le altre parti della memoria.
- Il taglio del testo è del domain: un testo più lungo della lunghezza si tronca a quella lunghezza, «…» compreso;
  con nessun limite entra intero.
- `all_decisions` spenta: entrano solo apri, chiudi e inverti; aggiorna e mantieni non entrano e non contano nel
  numero di decisioni ricordate. Accesa: entrano tutte le decisioni del flusso sull'asset e contano tutte. La regola sta
  nel domain di `FlowMemory`; la porta delle decisioni precedenti riceve dalla memoria le azioni da leggere, così
  l'adapter `sqlalchemy/` non ripete l'elenco.
- Migrazione: i flussi esistenti, con la memoria attiva o no, ricevono lunghezza 160 e «tutte le decisioni» spenta.
- API, strumenti MCP, esportazione e importazione della strategia, differenze tra le versioni e modulo del flusso
  portano le due parti nuove con lo stesso tipo della richiesta di memoria già condiviso da API e MCP. Nel modulo:
  campo «Lunghezza del motivo» con la scelta «illimitata» e casella «Tutte le decisioni», nella sezione «Memoria»,
  abilitati solo con la memoria attiva. Nell'API e negli strumenti «illimitata» è `null` nella lettura; nella richiesta
  si distingue «non indicata» (resta il valore in vigore) da «illimitata» come per le altre parti che si possono
  togliere.

### Esito delle aperture (Task 745)

- L'esito di un'apertura o un'inversione dice come si è chiusa la posizione (la causa di chiusura già registrata con la
  posizione chiusa: decisione dell'agente, stop loss, take profit, chiusura fuori dalla piattaforma che comprende la
  liquidazione, e ogni altra causa che la piattaforma registra) e dopo quanto tempo dall'apertura; una posizione ancora
  aperta dice da quanto tempo è aperta, all'istante del ciclo. L'adapter `sqlalchemy/` legge causa, apertura e chiusura
  da `closed_positions` e dalla posizione aperta del flusso.
- La durata si scrive in italiano con l'unità più grande sensata (minuti, ore, giorni). Testo della voce, per esempio:
  «apri long, prezzo 0,002452, chiusa dallo stop loss dopo 12 minuti, PnL realizzato -2,32: <motivo>».
- Lettura della memoria (dashboard, API, MCP) e memoria registrata con il ciclo mostrano le voci come le riceve
  l'agente: motivo, invalidazione, causa e durata nei tipi del domain già condivisi.

## Alternative scartate

- **Lunghezza fissa** (scelta dello sviluppo in R5.3.4): il proprietario la vuole configurabile.
- **Motivo estratto dal ragionamento** (prima frase): i ragionamenti cominciano dal contesto di mercato.
- **Motivo obbligatorio nella risposta**: farebbe fallire i cicli dei flussi con un system prompt personalizzato
  precedente.
- **Aggiornamenti sempre in memoria**: senza esito proprio, e lo stop e l'obiettivo in vigore l'agente li vede già
  nello stato della posizione aperta.

## Conseguenze

- Due colonne in più in `cycle_decisions` e due parti in più nella memoria della versione del flusso (migrazione con
  i predefiniti).
- Con «tutte le decisioni» accesa le decisioni di mantenere, frequenti, riempiono presto la memoria: è una scelta
  dell'utente.
- L'ADR memoria-del-flusso-dalle-decisioni-operative-precedenti diventa superata.
