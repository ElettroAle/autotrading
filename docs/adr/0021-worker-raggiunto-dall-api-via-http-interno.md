# ADR 0021 — Worker raggiunto dall'API via HTTP interno, unico detentore della chiave privata

- Stato: accettata (10 novembre 2026)
- Requisiti: R0.2.2, R0.2.3, R0.1.3

## Contesto

R0.2.2 chiede lo stato aggiornato di un conto: saldo, margine disponibile, posizioni aperte, letti
dall'exchange alla richiesta. Per leggerlo servono le credenziali salvate, che solo il `worker` può
decifrare (ADR 0007). Il proprietario ha stabilito che l'API parla con il `worker` via HTTP interno.
Restano da decidere: come si divide il lavoro tra i due servizi, come il `worker` si fida della
richiesta, come riceve la chiave privata e come si legge lo stato su Hyperliquid.

## Decisione

- **Due casi d'uso, uno per servizio.**
  - `ReadAccountStateUseCase` (API) cerca il conto nel tenant della richiesta, sotto RLS. Un conto di un
    altro tenant risponde "non trovato" e non arriva mai al `worker` (R0.1.3). Poi chiede lo stato alla
    porta `AccountStatePort`.
  - `ReadExchangeStateUseCase` (`worker`) ritrova il conto sotto RLS per il tenant indicato, sceglie
    l'exchange, apre le credenziali con `CredentialOpenerPort` e legge lo stato con la stessa verifica
    firmata della registrazione. Il messaggio di un rifiuto si oscura (ADR 0020).
- **Porta `ExchangePort.read_state`** al posto di `read_balance`. La registrazione e la sostituzione
  usano il saldo dello stato. Su Hyperliquid:
  - saldo da `marginSummary.accountValue`;
  - margine disponibile da `withdrawable`;
  - posizioni da `assetPositions`: segno di `szi` per la direzione, leva, prezzo di ingresso, risultato
    non realizzato e prezzo di liquidazione, che può mancare;
  - istante della lettura da `time` dell'exchange.
  Una risposta di forma inattesa è "exchange non raggiungibile", mai valori inventati.
- **HTTP interno**:
  - Il `worker` espone `GET /tenants/{tenant}/accounts/{conto}/state` e `/health`, senza pagina OpenAPI.
  - Non pubblica porte: lo raggiunge solo l'API sulla rete del compose (`WORKER_URL=http://worker:8000`).
  - Ogni richiesta porta `Authorization: Bearer <token>`. Il token è di 48 caratteri, generato da
    `prepare-installation.sh` sulla macchina e montato come file nei soli `api` e `worker`. Il `worker`
    lo confronta in tempo costante; un token vuoto non è mai valido.
  - Il tenant viaggia nel percorso perché l'API l'ha già risolto dall'identità; il `worker` lo accetta solo
    da chi presenta il token.
- **Adapter `HttpxAccountStateAdapter`** in `adapters/outbound/httpx/`, timeout di 15 secondi, nessun
  nuovo tentativo. Le risposte del `worker` tornano errori della porta:
  - 404: "non trovato";
  - 422 con `exchange_message`: credenziali rifiutate;
  - 503: exchange non raggiungibile;
  - qualunque altra risposta, rete o forma inattesa: `WorkerUnavailableError` "servizio di esecuzione non
    raggiungibile, riprovare" (503).
  Le credenziali non aprono (testo di un altro conto, versione senza chiave): `CredentialsNotOpenedError`,
  500, perché è un guasto dell'installazione e non della richiesta. `httpx` passa tra le dipendenze di
  esercizio.
- **Chiave privata**: `SodiumCredentialOpenerAdapter` riceve le chiavi per versione e sceglie quella
  salvata con il testo cifrato; rifiuta un testo il cui tenant o conto non coincide.
  - Il file `credentials_private_key_v1` appartiene all'utente dell'immagine (65532) con modo 0400, a ogni
    rilascio, anche per le installazioni create prima del `worker`.
  - Lo monta solo il servizio `worker`. L'API gira con lo stesso utente ma non lo monta: l'isolamento sta
    nel montaggio, come per gli altri segreti.
- **Composizione**: `bootstrap.create_worker_application` costruisce il `worker` con la stessa immagine
  dell'API e un altro comando di uvicorn; `TenantUseCases.on` riceve la porta dello stato.

## Alternative scartate

- **API che decifra**: porta la chiave privata nel servizio esposto agli utenti, contro ADR 0007.
- **Coda o tabella di richieste nel database**: latenza e polling per una lettura sincrona; nessun
  vantaggio finché c'è un solo `worker`.
- **Nessuna autenticazione sulla rete interna**: qualunque container dell'installazione (oggi PostgreSQL)
  potrebbe chiedere credenziali decifrate in uso per qualunque tenant.
- **mTLS tra i servizi**: una CA da gestire sulla macchina per due servizi sulla stessa rete privata; il
  token copre la stessa minaccia.
- **Lettura dello stato senza verifica firmata** (solo `clearinghouseState`): non accorgersi che le
  credenziali non sono più accettate, contro l'ultimo scenario di R0.2.2.
- **Codici di errore nel corpo delle risposte del `worker`**: un campo in più nel contratto. Stato HTTP e
  campi già presenti bastano a ricostruire l'errore.

## Conseguenze

- Un exchange non supportato dal `worker` ma presente nel conto risponde "servizio di esecuzione non
  raggiungibile": succede solo con una configurazione diversa tra i due servizi, che hanno la stessa
  immagine e lo stesso ambiente.
- La macchina `d2-2` esegue un processo Python in più.
