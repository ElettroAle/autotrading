# ADR 0098 — Chiamata ai modelli tramite il proxy LiteLLM con la chiave dell'utente

- Stato: accettata (13 novembre 2026) per la parte conforme a `docs/architecture.md`; gli scostamenti elencati
  sotto attendono la conferma del proprietario
- Requisiti: R1.4.4, R1.4.6, R1.2.3, R1.2.4, RF-01.05, RF-16.04; Bug B1.4.2 (181)
- Supera: ADR 0039 (chiamata diretta ai quattro fornitori con un adapter httpx)
- Collegate: ADR 0007 (solo il worker decifra), ADR 0015 (segreti come file generati sulla macchina), ADR 0029
  (chiavi dei fornitori dell'utente), ADR 0030 (catalogo, superato a sua volta dall'ADR del catalogo da LiteLLM)

## Contesto e problema

`docs/architecture.md` prescrive un proxy LiteLLM self-hosted come unico accesso ai modelli (righe 19 e 51), un
container `litellm` sulla rete interna dell'installazione (righe 238 e 288) e nessun adapter per fornitore: il
client parla con LiteLLM tramite l'SDK OpenAI con il `base_url` del proxy (riga 169). L'ADR 0039 aveva invece
scritto un adapter httpx che chiamava direttamente Anthropic, OpenAI, DeepSeek e OpenRouter, ciascuno con il suo
corpo e le sue intestazioni, rinviando il proxy: uno scostamento non autorizzato dall'architettura.

Vincolo funzionale: la chiave di un fornitore IA è dell'utente e si usa solo per i suoi flussi (RF-01.05, RF-16.04,
ADR 0029). `docs/architecture.md:228-231` parla invece di chiavi dei fornitori della piattaforma montate nel proxy e
di una chiave virtuale per tenant: qui vincono i requisiti.

## Decisione

### Container `litellm` (deploy)

- Immagine ufficiale non root `ghcr.io/berriai/litellm-non_root`, fissata per digest (`main-v1.83.14-stable`), utente
  65534, filesystem in sola lettura con `/tmp` in memoria, nessuna porta pubblicata: lo raggiungono solo `worker` e
  `api` all'indirizzo interno `http://litellm:4000`.
- Configurazione in `deploy/litellm/config.yaml`, senza segreti: una rotta wildcard per fornitore abilitato
  (`anthropic/*`, `deepseek/*`, `openai/*`, `openrouter/*`), nessuna chiave dei fornitori.
  - `drop_params`: un parametro non accettato da un modello si toglie invece di far fallire il ciclo;
  - `turn_off_message_logging`: né messaggi né risposte nei log del proxy;
  - `num_retries: 0`: il nuovo tentativo è il ciclo successivo, un tentativo del proxy spenderebbe di nuovo il
    credito dell'utente;
  - `disable_cooldowns`: le rotte sono condivise da tutti i tenant; senza questa impostazione il rifiuto della chiave
    di un utente metteva in pausa la rotta per tutti (provato in locale: 429 «No deployments available»).
- Chiave master del proxy generata sulla macchina da `prepare-installation.sh` (`secrets/litellm_master_key`,
  utente 65532, 0400), montata come file in `worker` e `api` (`LITELLM_MASTER_KEY_FILE`). Il file montato nel proxy
  (`secrets/litellm_config`, utente 65534, 0400) è il modello del repository più `general_settings.master_key`; se
  cambia, il rilascio ricrea solo il proxy. Nessun segreto in variabili d'ambiente (ADR 0015).
- Rilascio solo dalla pipeline: l'action `ssh-deploy` copia il modello della configurazione prima di
  `prepare-installation.sh`.

### Adapter `LiteLlmModelCallAdapter` (`adapters/outbound/litellm/`)

- Una cartella, una tecnologia: l'SDK `openai` (`OpenAI(base_url=proxy, api_key=chiave master, max_retries=0)`),
  importato solo lì; `bootstrap.py` riceve l'adapter già costruito da `litellm_model_call(url, chiave master)`.
- Realizza `ModelCallPort` senza cambiarne il contratto. Il nome del modello è quello di LiteLLM
  (`<fornitore>/<modello>`), passato così com'è.
- La chiave dell'utente viaggia nel corpo della richiesta (`api_key`), che LiteLLM usa al posto della chiave della
  rotta solo per quella richiesta: nessuna chiave dei fornitori resta nel proxy.
- Parametri: `max_tokens` (4096 se il flusso non lo indica), `temperature`; risposta JSON obbligata solo per OpenAI e
  DeepSeek, come prima. Livello di ragionamento (basso, medio, alto in low, medium, high), solo se il flusso lo
  imposta, cioè solo se il catalogo dichiara che il modello lo supporta:
  - Anthropic: `output_config.effort`, passato al fornitore. `reasoning_effort` non va bene: LiteLLM lo traduce in un
    budget di thinking di 4096 token per i modelli che non riconosce, maggiore del limite del flusso;
  - OpenRouter: `reasoning.effort`, passato al fornitore (`reasoning_effort` verrebbe tolto da `drop_params`);
  - ogni altro fornitore, compreso uno abilitato in seguito nella configurazione: `reasoning_effort`, tradotto da
    LiteLLM. Nessun elenco di fornitori nell'adapter: lo decide la configurazione del proxy.
- Costo: solo quello che il fornitore dichiara (`usage.cost` di OpenRouter, che LiteLLM conserva nella risposta);
  la stima di LiteLLM non si usa, così i prezzi del catalogo restano l'unica fonte per gli altri fornitori (R1.4.6).
- Errori, invariati per l'utente (R1.2.3, R1.2.4):
  - 401 o 403 dal fornitore: `ModelKeyRejectedError`, permanente;
  - 402, o 429 con «insufficient_quota» o «exceeded your current quota» nel messaggio: `ModelCreditExhaustedError`,
    permanente. Il proxy conserva il messaggio di OpenAI ma non il suo codice, da qui la ricerca nel testo;
  - ogni altro rifiuto: `ModelUnavailableError` con lo stato e il messaggio originale, senza il suffisso di
    instradamento del proxy («Received Model Group=…»), compattato, tagliato a 300 caratteri e ripulito dalla chiave;
  - una chiave master che il proxy non conosce risponde 400 («No connected db.»): transitorio, non tocca i flussi;
  - tempo scaduto (120 secondi), rete e risposta di forma inattesa: transitori;
  - gli errori dell'SDK portano la richiesta, e con essa la chiave nel corpo: si rilanciano senza causa.
- Prova dal vivo (marcatore `providers`): ogni modello riceve una chiave inventata attraverso un proxy LiteLLM e
  il fornitore la rifiuta, senza consumare credito.

## Confronto con le decisioni scritte

- `docs/architecture.md:19, 51, 169, 238, 288`: rispettate (proxy self-hosted, container sulla rete interna, SDK
  OpenAI con `base_url` del proxy, nessun adapter per fornitore).
- `docs/requirements.md` RF-01.05, RF-16.04 e ADR 0029: rispettati, la chiave dell'utente si usa solo nella richiesta
  del suo flusso.
- CLAUDE.md, regola delle dipendenze: `openai` solo in `adapters/outbound/litellm`; nuova cartella nei contratti di
  import-linter e nella mappa delle librerie del test di architettura.
- CLAUDE.md, sicurezza: nessun segreto in variabili d'ambiente, rilascio dalla pipeline.

## Scostamenti

1. **Chiavi della piattaforma e chiave virtuale per tenant** (`docs/architecture.md:228, 231`): nessuna chiave dei
   fornitori nel proxy e nessuna chiave virtuale. Motivo: RF-01.05 e ADR 0029, le chiavi sono dell'utente.
2. **Registro spesa e budget in LiteLLM, metadata tenant/flusso/ciclo** (`docs/architecture.md:17, 19, 169, 312`):
   il proxy gira senza database. Motivi: nessun requisito chiede un budget (RF-28.08 è una stima, F5, proposta);
   il costo di ogni chiamata è già registrato nel ciclo del flusso, nel tenant (R1.4.6), e un secondo registro
   duplicherebbe quel calcolo; il database di LiteLLM richiederebbe un altro schema con le sue migrazioni Prisma.
   Senza database i metadata non hanno dove finire e non si inviano.
3. **Verifica delle chiavi alla registrazione**: resta diretta presso il fornitore (adapter httpx, ADR 0029).
   LiteLLM non ha un controllo gratuito di una chiave passata dal client: l'unico controllo che offre è una
   chiamata al modello, che spenderebbe il credito dell'utente (ADR 0029 vieta di consumarlo).

## Conseguenze

- Un fornitore nuovo è una rotta in `deploy/litellm/config.yaml` più la sua verifica delle chiavi (scostamento 3);
  un test confronta le rotte della configurazione con le verifiche disponibili.
- Il `worker` e l'`api` dipendono dal proxy solo a richiesta: se il proxy è giù fallisce la chiamata (ciclo
  transitorio), non l'avvio dei servizi.
- Il proxy aggiunge circa 350 MB di memoria all'installazione `dev` (misurato in locale); con `d2-2` va osservato.
