# ADR 0039 — Chiamata al modello con un adapter httpx per fornitore

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.4.4, R1.4.6, R1.2.3, R1.2.4 (Task T1.4.4.1, T1.4.6.1)

## Contesto

A ogni ciclo il `worker` chiama il modello del flusso presso il suo fornitore (Anthropic, OpenAI, DeepSeek,
OpenRouter), con la chiave dell'utente (ADR 0007, 0029), i parametri del flusso (temperatura, limite di
lunghezza, livello di ragionamento; ADR 0030) e i messaggi del contesto (ADR 0038). Servono il testo della
risposta e il consumo (token e, se c'è, costo). Gli errori vanno divisi in permanenti, che mettono in pausa i
flussi (credito esaurito, chiave non valida: R1.2.4), e transitori, che fanno fallire solo il ciclo con il
messaggio originale (R1.2.3). L'architettura prevedeva LiteLLM in una fase successiva; i modelli del catalogo
ne usano già la convenzione di nome `<fornitore>/<modello>`.

## Decisione

- **Porta** `ModelCallPort.call(modello, chiave, parametri, messaggi) -> ModelReply(testo, ModelUsage)` in
  `application/agent/ports.py`.
- **Adapter** `HttpxModelCallAdapter` in `adapters/outbound/httpx/model_call.py`, con una tabella `ProviderApi`
  per fornitore (URL, intestazioni, corpo, lettura della risposta), come per la verifica delle chiavi:
  - OpenAI: `/v1/chat/completions`, `max_completion_tokens`, `reasoning_effort`, risposta JSON obbligata;
  - DeepSeek: `/chat/completions`, `max_tokens`, risposta JSON obbligata;
  - OpenRouter: `/api/v1/chat/completions`, `reasoning.effort`; il formato JSON si chiede solo nel messaggio di
    sistema, perché non ogni modello instradato lo supporta; il costo arriva in `usage.cost`;
  - Anthropic: `/v1/messages`, sistema separato, `max_tokens` obbligatorio (4096 se il flusso non lo
    indica), `output_config.effort`; il testo è l'unione dei blocchi `text`.
  - Livelli di ragionamento: basso, medio, alto diventano low, medium, high.
- **Errori**:
  - 401 o 403: `ModelKeyRejectedError` "chiave del fornitore non valida: <fornitore>", permanente;
  - 402, e per OpenAI 429 con codice `insufficient_quota`: `ModelCreditExhaustedError` "credito esaurito presso
    <fornitore>", permanente;
  - ogni altro rifiuto, la rete, il tempo scaduto (120 secondi) e una risposta di forma inattesa:
    `ModelUnavailableError` "fornitore IA non raggiungibile: <fornitore>: <messaggio originale>", transitorio;
    il messaggio originale è compattato, tagliato a 300 caratteri e ripulito dalla chiave.
  - Gli errori della rete si rilanciano senza causa (`from None`): l'eccezione di httpx porta la richiesta, e con
    essa le intestazioni.
- **Prova dal vivo** con il marcatore `providers` (ADR 0029): ogni modello del catalogo riceve una chiave
  inventata e il fornitore la rifiuta, senza consumare credito.

## Alternative scartate

- **LiteLLM come libreria**: una dipendenza grande, con molti fornitori che non servono, per quattro API già
  documentate; la sua mappa degli errori non distingue credito esaurito e limite di frequenza di OpenAI.
- **LiteLLM come servizio (proxy)**: un container in più nell'installazione, con la chiave dell'utente che lo
  attraversa; utile con molti fornitori, rinviato.
- **SDK ufficiali dei fornitori**: quattro dipendenze per quattro richieste HTTP.
- **Un 400 come errore permanente**: Anthropic lo usa anche per i limiti di spesa, ma pure per richieste
  malformate; il requisito elenca come permanenti solo credito e chiave, il resto fa fallire il ciclo.

## Conseguenze

- Il ciclo (F1.2) decifra la chiave nel `worker`, costruisce il contesto, chiama la porta, legge la risposta con
  `AgentResponse.read` e registra consumo e costo.
- Un fornitore nuovo è una voce di `PROVIDER_APIS` più la sua verifica delle chiavi (ADR 0029).
