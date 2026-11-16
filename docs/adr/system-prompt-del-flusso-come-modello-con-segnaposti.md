# ADR system-prompt-del-flusso-come-modello-con-segnaposti — System prompt del flusso come modello con segnaposti dichiarati

- Stato: accettata (16 novembre 2026)
- Requisiti: R1.4.8 (US 435, Task 436), R1.4.3, R1.4.7, R1.1.3, R2.5.2
- Collegate: ADR 0038 (contesto e risposta dell'agente nel domain), ADR risposta-del-modello-con-schema-rigido,
  ADR prezzo-di-mercato-dichiarato-dall-exchange

## Contesto e problema

Il messaggio di sistema dell'agente era cablato in `AgentContext` per tutti i flussi, salvo le istruzioni. Il
proprietario vuole vederlo nella configurazione del flusso col suo predefinito e modificarlo per intero, con segnaposti
in inglese descritti nel pannello della configurazione, senza ripetere in più punti nomi e valori delle variabili.

## Fattori decisionali

- Un segnaposto si dichiara una volta sola: testo predefinito, controllo, sostituzione, API e dashboard ne derivano.
- Un flusso che non personalizza il prompt riceve gli aggiornamenti del predefinito.
- Lo schema rigido della risposta (Bug 416) e i controlli del codice non dipendono dal testo.
- Nessuna libreria esterna nel domain.

## Opzioni considerate

### 1. Modello di testo nella configurazione, segnaposti in un registro unico del domain `flows`

- `PromptPlaceholder` (`domain/flows/system_prompt.py`) è un `StrEnum` in cui ogni membro (`instructions`, `actions`,
  `max_leverage`, `assets`) dichiara descrizione e come si ricava il valore da `PromptSubject` (configurazione del
  flusso e azioni ammesse). Il testo predefinito scrive i segnaposti con `PromptPlaceholder.<membro>.slot`.
- `FlowConfiguration.system_prompt: str | None`: `None` è il predefinito della piattaforma. La configurazione controlla
  il modello quando nasce (`string.Formatter` della libreria standard, anche dentro le specifiche di formato): un
  segnaposto fuori registro è `UnknownPromptPlaceholderError`, una graffa senza coppia `MalformedSystemPromptError`;
  entrambi rifiuti di un'impostazione del flusso (422 col campo `system_prompt`, come gli altri). Una graffa letterale
  si scrive doppia.
- Il ciclo (`ComposeCycleContextUseCase`) rende il modello coi valori del flusso e passa il testo pronto nella domanda
  all'agente; le azioni ammesse le dichiara `agent` (`ListAgentActionsUseCase`, porta `AgentActionsPort` di `flows`),
  così `flows` non ripete le parole della risposta. `AgentContext` non ha più testo di sistema cablato: invia il prompt
  ricevuto, il messaggio coi dati del ciclo e lo schema della risposta restano invariati.
- Persistenza: chiave `system_prompt` nel documento JSON della versione in `flow_versions` (la configurazione è già un
  documento); una versione salvata prima la legge assente, cioè predefinita. Nessuna migrazione.
- API: flusso e versione restituiscono `system_prompt` (modello in vigore), `system_prompt_is_default` e
  `system_prompt_placeholders` (nome e descrizione dal registro); `GET /flows/system-prompt` dà predefinito e segnaposti
  per un flusso nuovo. La creazione accetta il testo o `null`; la modifica tiene il prompt se il campo manca e torna al
  predefinito con `null` esplicito.
- Il file della strategia (R2.5.2) porta il `system_prompt`, `null` per il predefinito.
- Dashboard: area di testo nel form del flusso, precompilata col predefinito, l'indicazione "predefinito", il pulsante
  "Ripristina predefinito" e sotto l'elenco dei segnaposti letto dall'API.

### 2. Solo le regole operative modificabili

Il proprietario vuole l'intero system prompt.

### 3. Nomi dei segnaposti ripetuti in predefinito, controllo, sostituzione, API e dashboard

Duplicazione e stringhe magiche: un segnaposto nuovo andrebbe aggiunto in cinque punti.

### 4. Motore di template esterno (Jinja)

Una libreria nel domain, vietata; `string.Formatter` basta e non permette accesso ad attributi (`{assets.x}` è un
segnaposto sconosciuto).

### 5. Testo predefinito copiato nella configurazione alla creazione

Il flusso non riceverebbe gli aggiornamenti del predefinito.

## Esito della decisione

Opzione 1: un segnaposto nuovo si aggiunge in un solo punto, il registro; il testo predefinito resta della piattaforma
finché l'utente non lo cambia; lo schema della risposta resta vincolante anche se il testo non descrive il formato.

## Conseguenze

- Il formato della risposta nel testo predefinito è una guida per il modello; lo schema rigido passato al fornitore e la
  lettura di `AgentResponse` restano il controllo.
- Un prompt personalizzato può togliere le regole operative dal testo: validazione e controllo del rischio restano nel
  codice e non cambiano.
- Le differenze tra versioni riportano la parte "system prompt" ("predefinito" quando segue la piattaforma).
