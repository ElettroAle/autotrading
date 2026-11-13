# ADR 0108 — Nessuna verifica preventiva della chiave IA

- Stato: accettata (13 novembre 2026), decisione del proprietario
- Requisiti: R1.4.1, R1.2.4; Bug B0.0.3 (177)
- Supera: ADR 0029 nella parte di verifica della chiave alla registrazione e alla sostituzione; ADR 0101 scostamento
  3 e ADR 0103 scostamento 4 (un fornitore nuovo richiede il controllo della sua chiave)
- Collegate: ADR 0101 (chiamata ai modelli tramite il proxy LiteLLM), ADR 0103 (catalogo da LiteLLM)

## Contesto e problema

Alla registrazione e alla sostituzione la piattaforma verificava la chiave presso il fornitore con un endpoint
gratuito (ADR 0029), da `adapters/outbound/httpx/provider_key_verifier.py`. Quella cartella violava CLAUDE.md (una
cartella per sistema integrato, mai una cartella `httpx/`; un adapter = una sola tecnologia) e un fornitore nuovo
richiedeva, oltre alla rotta nel proxy LiteLLM, il suo controllo della chiave. Spostare la verifica in una cartella
per fornitore (PR #118, chiusa) portava codice ripetuto in quattro adapter.

Il proprietario ha deciso il 13 novembre 2026: nessuna verifica preventiva. Una chiave errata emerge al primo ciclo
come errore permanente: il flusso va in pausa con «chiave del fornitore non valida: <fornitore>» (R1.2.4, già
realizzato da `ModelKeyRejectedError`).

## Decisione

- La registrazione e la sostituzione di una chiave non interrogano il fornitore: controllano fornitore del catalogo,
  chiave non vuota e, alla registrazione, assenza di una chiave già presente; poi sigillano e salvano.
- Eliminati `adapters/outbound/httpx/` (cartella e adapter), `ProviderKeyVerifierPort`, gli errori
  `ProviderRejectedKeyError`, `ProviderUnavailableError`, `ProviderNotVerifiableError`, il fake, i test dell'adapter,
  la prova dal vivo e il test che confrontava le rotte del proxy con i controlli della chiave.
- `bootstrap.py` non crea più il client `httpx` della verifica: tolte da `known_violations.py` le voci
  `bootstrap.py:httpx` e `bootstrap.py:PROVIDER_TIMEOUT_SECONDS`.
- Un fornitore nuovo è solo una rotta in `deploy/litellm/config.yaml`.
- R1.4.1 (board e `.feature`) non promette più la verifica: tolti lo scenario della chiave rifiutata e le condizioni
  «il fornitore accetta la chiave»; il testo dice che una chiave non valida si scopre al primo ciclo (R1.2.4).

## Alternative scartate

- **Una cartella per fornitore con il suo verificatore** (PR #118): conforme a CLAUDE.md ma con quattro adapter quasi
  uguali e una cartella in più per ogni fornitore; superata dalla decisione del proprietario.
- **Verifica tramite il proxy LiteLLM**: nessun controllo gratuito; una chiamata a un modello spenderebbe il credito
  dell'utente (ADR 0103).

## Conseguenze

- Una chiave sbagliata si registra senza errore; il primo ciclo di un flusso che la usa la rifiuta e mette in pausa
  i flussi di quel fornitore con il motivo e la notifica (R1.2.4).
- Meno dipendenze in uscita dall'`api`: nessuna chiamata verso i fornitori IA.

## Confronto con le decisioni scritte

- CLAUDE.md:110-116 (tecnologia = sistema integrato, mai una cartella `httpx/`): rispettato, la cartella è eliminata.
- CLAUDE.md:124 (`bootstrap.py` senza costanti né tecnologie): rispettato, tolti `PROVIDER_TIMEOUT_SECONDS` e `httpx`.
- docs/requirements.md RF-01.05 (chiavi dell'utente usate solo per i suoi flussi): invariato.
- R1.2.4 (errore permanente del fornitore IA, flusso in pausa): è il punto in cui una chiave non valida emerge.
- docs/architecture.md §5 (accesso ai modelli via LiteLLM): aggiornato, la verifica alla registrazione non c'è più.
- Scostamenti: nessuno.
