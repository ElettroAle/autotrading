---
paths:
  - "src/autotrading/*/agent/**"
  - "tests/**/agent/**"
  - "specs/E1-flussi-autonomi/F1.4-agente-ia/**"
---

# Contesto agent

L'agente IA: chiavi dei fornitori, modelli, contesto, decisione e costo.

## Glossario

- **Provider key**: chiave dell'utente presso un fornitore di modelli, al massimo una per fornitore,
  verificata presso il fornitore alla registrazione e alla sostituzione (R1.4.1). È una mappa sui campi che il
  catalogo dichiara per quel fornitore (`api_key` se non ne dichiara altri, R2.3.9, ADR 0159).
- **Model catalog**: modelli disponibili con fornitore, nome, parametri ammessi, valori predefiniti e
  prezzi (R1.4.2).
- **Agent context**: istruzioni del flusso, regole operative, ora, stato del flusso, dati delle fonti con
  i pesi, dati mancanti (R1.4.3). Riguarda solo il flusso.
- **Decision**: per ogni asset del flusso, `open` (long o short, quota dei soldi del flusso da 0 a 1, leva),
  `close` (sempre totale) o `hold`, con il ragionamento (R1.4.4).
- **Non-conforming decision**: campo mancante, valore fuori tipo o intervallo, azione non ammessa, asset
  non del flusso; si scarta con il motivo. Un asset senza decisione vale `hold`, registrato come mancante
  (R1.4.5).
- **Call cost**: token in ingresso e in uscita e costo in USD per chiamata; dal fornitore, altrimenti dal
  catalogo, altrimenti non disponibile (R1.4.6).

## Regole

- Le chiavi dei fornitori si conservano come le credenziali dei conti (ADR 0007): cifrate con la chiave
  pubblica, decifrabili solo dal `worker`, mai in una risposta, in un log o nel contesto.
- Un flusso usa solo modelli di fornitori di cui l'utente ha la chiave.
- Nessun limite di spesa sulla piattaforma: il flusso va in pausa solo quando il fornitore dichiara il
  credito esaurito o la chiave non valida (errore permanente, ciclo decisionale di `flows`).
- Una risposta non leggibile per intero scarta tutte le decisioni; nessun nuovo tentativo nello stesso ciclo.
- Le posizioni aperte nel contesto portano prezzo di mercato e PnL non realizzato dell'exchange del conto e le regole
  operative dicono di valutarle solo con quelli: le fonti possono leggere un'altra rete o piazza (R1.4.7, ADR
  prezzo-di-mercato-dichiarato-dall-exchange).
- Formato della risposta, lettura delle decisioni, contesto e costo sono regole del domain (`AgentResponse`,
  `AgentContext`, `ModelUsage`, ADR 0038): le chiavi della risposta sono i nomi dei campi dei motivi di scarto.
- Il modello riceve il formato delle decisioni come vincolo (`DECISIONS_FORMAT`, schema JSON rigido costruito dalle
  chiavi di `AgentResponse`): `AskAgentUseCase` lo passa a `ModelCallPort.call` e l'adapter lo fa imporre al fornitore
  dove il modello lo supporta. La lettura di `AgentResponse` resta il controllo finale (ADR
  risposta-del-modello-con-schema-rigido).
- La chiamata al modello passa dalla libreria LiteLLM nel solo `worker` (`adapters/outbound/litellm`, ADR 0148) o
  dall'API di OpenRouter (ADR 0109): la chiave dell'utente viaggia nella sola chiamata del suo flusso, nessuna
  chiave dei fornitori della piattaforma. 401/403 chiave non valida e 402 (o quota OpenAI esaurita) credito
  esaurito sono permanenti, ogni altro errore è transitorio con il messaggio originale.

- La chiave non si verifica presso il fornitore alla registrazione né alla sostituzione: una chiave non valida
  emerge al primo ciclo come `ModelKeyRejectedError`, permanente (R1.2.4, ADR 0108).
- Il catalogo LiteLLM viene dalla mappa dei modelli della libreria (ADR 0148): i modelli di chat dei fornitori
  abilitati nell'adapter, con parametri e prezzi della mappa; l'`api` lo chiede al `worker` (ADR 0149). Abilitare
  un fornitore è solo un nome nelle impostazioni dell'adapter; nessun catalogo scritto a mano. I casi d'uso che
  leggono solo i modelli ricevono i cataloghi (`ModelCatalogs`), non le fabbriche.

## Porte del contesto

Repository delle chiavi, cifratura e decifratura delle chiavi, verifica presso il fornitore, catalogo dei
modelli, chiamata al modello con risposta strutturata e costo.
