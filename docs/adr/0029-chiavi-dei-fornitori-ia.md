# ADR 0029 — Chiavi dei fornitori IA: verificate dall'API, sigillate come le credenziali dei conti

- Stato: accettata (11 novembre 2026)
- Requisiti: R1.4.1 (Task T1.4.1.1)

## Contesto

R1.4.1 chiede che ogni utente registri al massimo una chiave per fornitore di modelli IA, la sostituisca e la
rimuova. Alla registrazione e alla sostituzione la chiave si verifica presso il fornitore, e una chiave
rifiutata non si registra. La chiave è conservata come le credenziali dei conti: mai in una risposta, in un
log o nel contesto dell'agente, e la usa solo il servizio che esegue i cicli. La rimozione di una chiave usata
da flussi attivi o in pausa è rifiutata. I flussi (R1.1.1) e i cicli (F1.2) non esistono ancora.

## Decisione

- **Domain di `agent`**: `ProviderName`, `ProviderKey` (rappresentazione mascherata, `redact`),
  `SealedProviderKey` (versione della chiave e testo cifrato), `RegisteredProviderKey` (`TenantOwned`: tenant,
  fornitore, chiave sigillata).
- **Verifica dall'API**, che riceve la chiave in chiaro solo durante la richiesta, come per le credenziali dei
  conti (ADR 0007). `ProviderKeyVerifierPort` ha un adapter httpx che interroga un endpoint gratuito del
  fornitore che richiede la chiave e non consuma credito:
  `GET https://api.anthropic.com/v1/models` (`x-api-key`, `anthropic-version`),
  `GET https://api.openai.com/v1/models`, `GET https://api.deepseek.com/models`,
  `GET https://openrouter.ai/api/v1/key` (OpenRouter elenca i modelli anche senza chiave).
  200 vuol dire accettata; 401 o 403 vuol dire rifiutata (`ProviderRejectedKeyError`, 422, "chiave rifiutata
  dal fornitore: <fornitore>"); qualunque altro esito, o un errore di rete, vuol dire fornitore non
  raggiungibile (`ProviderUnavailableError`, 503). Né la chiave né la risposta del fornitore entrano in un
  errore o in un log.
- **Sigillo con la chiave pubblica dell'installazione** (`ProviderKeySealerPort`, adapter libsodium): il testo
  sigillato nomina tenant e fornitore, così il `worker` rifiuterà una chiave copiata su un altro tenant o
  fornitore. L'apertura arriva con i cicli, solo nel `worker`.
- **Tabella `provider_keys`**: chiave primaria (tenant, fornitore), quindi al massimo una chiave per fornitore,
  con row level security come `accounts` (ADR 0018). La sostituzione aggiorna la riga e la rimozione la
  cancella: una chiave non ha storia da conservare.
- **Fornitori ammessi**: quelli dei modelli del catalogo (ADR 0030). Un fornitore fuori catalogo dà
  `UnsupportedProviderError` (422) con l'elenco degli ammessi.
- **Rimozione e flussi**: `ProviderKeyUsagePort` dice quali flussi attivi o in pausa usano il fornitore. Finché
  i flussi non esistono, il bridge in `bootstrap.py` non ne trova nessuno. R1.1.1 lo collegherà al contesto
  `flows`, e lo scenario della rimozione rifiutata resta `@wip` fino ad allora.
- **API**: `POST /provider-keys` (201), `GET /provider-keys`, `PUT /provider-keys/{fornitore}`,
  `DELETE /provider-keys/{fornitore}` (204). Le risposte nominano solo il fornitore.

## Alternative scartate

- **Verifica con una chiamata di completamento minima**: consuma credito dell'utente a ogni registrazione.
- **Verifica attraverso LiteLLM**: il proxy non ha un endpoint di sola verifica della chiave, e una chiamata
  di completamento costa come sopra.
- **Verifica dal `worker`**: l'API ha già la chiave in chiaro durante la richiesta; mandarla al `worker` la
  esporrebbe su un'altra connessione senza alcun guadagno.

## Conseguenze

- Un fornitore nuovo nel catalogo richiede il suo endpoint di verifica nell'adapter. Un test di bootstrap
  controlla che ogni fornitore del catalogo ne abbia uno.
- I test di integrazione provano contro i fornitori veri che una chiave inventata viene rifiutata, senza
  bisogno di segreti.
