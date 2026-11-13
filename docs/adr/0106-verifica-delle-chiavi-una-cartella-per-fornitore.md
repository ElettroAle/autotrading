# ADR 0106 — Verifica delle chiavi: una cartella per fornitore

- Stato: accettata (13 novembre 2026)
- Requisiti: R1.4.1; Bug B0.0.3 (177)
- Supera: la parte di ADR 0029 che metteva il verificatore in `adapters/outbound/httpx/`
- Collegate: ADR 0029 (chiavi dei fornitori dell'utente), ADR 0103 (catalogo da LiteLLM, verifica diretta presso il
  fornitore)

## Contesto e problema

La verifica della chiave di un fornitore IA alla registrazione e alla sostituzione (R1.4.1) stava in
`adapters/outbound/httpx/provider_key_verifier.py`: un solo adapter che parlava con quattro sistemi diversi
(Anthropic, OpenAI, DeepSeek, OpenRouter) ed era messo nella cartella della libreria di trasporto. CLAUDE.md dice che
una tecnologia è il sistema integrato, non la libreria che lo raggiunge («una chiamata HTTP verso Telegram sta in
`telegram/`, mai in una cartella `httpx/`»), e che un adapter è una sola tecnologia. Il client `httpx` era creato in
`bootstrap.py` (`PROVIDER_TIMEOUT_SECONDS`, `bootstrap.py:httpx` tra le violazioni note del Bug 177).

La verifica resta diretta presso il fornitore e non passa da LiteLLM: il proxy non ha un controllo gratuito della
chiave (ADR 0103).

## Decisione

- **Una cartella per fornitore**: `adapters/outbound/anthropic/`, `deepseek/`, `openai/`, `openrouter/`. Ognuna ha
  `key_verifier.py` con `<Fornitore>ProviderKeyVerifierAdapter` (realizza `ProviderKeyVerifierPort`, endpoint gratuito
  e intestazioni del proprio fornitore), `configuration.py` con `_<Fornitore>Settings` (timeout) e `composition.py`
  con `<fornitore>_adapters() -> {nome del fornitore: adapter}`, che crea il proprio client `httpx`.
- **La scelta del verificatore è del caso d'uso.** `ProviderKeyServices` riceve `verifiers: Mapping[str,
  ProviderKeyVerifierPort]` e sceglie per nome del fornitore; un fornitore del catalogo senza verificatore solleva
  `ProviderNotVerifiableError` (500), prima sollevato dall'adapter unico. È la stessa forma di `exchanges` per nome
  (Bug 177, #105).
- **`bootstrap.py`** unisce i dizionari delle quattro composizioni: nessun client, nessuna costante.
- La porta non cambia firma; il suo contratto non comprende più `ProviderNotVerifiableError`.
- Un test confronta le rotte wildcard di `deploy/litellm/config.yaml` con le cartelle che verificano le chiavi: un
  fornitore nuovo nel proxy senza la sua cartella è un test rosso. Un test di architettura vieta una cartella di
  tecnologia chiamata come una libreria di trasporto.
- Rule `.claude/rules/tech-ai-providers.md`, una per i quattro fornitori perché le cartelle hanno la stessa forma.

## Alternative scartate

- **Una cartella `ai_providers/` con i quattro controlli**: quattro sistemi in un adapter, contro «un adapter = una e
  una sola tecnologia».
- **Verifica tramite il proxy LiteLLM**: nessun controllo gratuito; una chiamata a un modello spenderebbe il credito
  dell'utente (ADR 0103).
- **Il dizionario dei verificatori dentro un adapter che smista**: un adapter che riceve altri adapter e sceglie,
  cioè un adapter che orchestra; la scelta appartiene al caso d'uso.

## Conseguenze

- Il codice di traduzione degli esiti (200, 401/403, altro) si ripete nelle quattro cartelle: ognuna resta staccabile
  e le cartelle di tecnologia non si importano a vicenda.
- Un fornitore nuovo richiede la sua cartella, la sua rotta nel proxy e la voce in `bootstrap.py`.
- Tolte da `known_violations.py`: `bootstrap.py:httpx`, `bootstrap.py:PROVIDER_TIMEOUT_SECONDS`.

## Confronto con le decisioni scritte

- CLAUDE.md:110-116 (tecnologia = sistema integrato, `httpx` libreria di trasporto, mai una cartella `httpx/`):
  rispettato, la cartella è eliminata.
- CLAUDE.md:117-120 (il caso d'uso orchestra; un adapter non riceve porte): rispettato, la scelta per nome è in
  `ProviderKeyServices`.
- CLAUDE.md:124 (`bootstrap.py` senza costanti né tecnologie): rispettato, tolto `PROVIDER_TIMEOUT_SECONDS` e
  l'import di `httpx`.
- docs/architecture.md (chiavi dei fornitori dell'utente, verifica alla registrazione, R1.4.1): invariato per
  l'utente.
- Scostamenti: nessuno.
