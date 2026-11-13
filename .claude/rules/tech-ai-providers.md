---
paths:
  - "src/autotrading/adapters/outbound/anthropic/**"
  - "src/autotrading/adapters/outbound/deepseek/**"
  - "src/autotrading/adapters/outbound/openai/**"
  - "src/autotrading/adapters/outbound/openrouter/**"
  - "tests/unit/adapters/test_provider_key_verifiers.py"
  - "tests/integration/providers/**"
---

# Adapter in uscita: fornitori IA (verifica delle chiavi)

- Ogni fornitore è un sistema integrato a sé: una cartella per fornitore (`anthropic/`, `deepseek/`, `openai/`,
  `openrouter/`), con `httpx` come trasporto. Le chiamate ai modelli passano dal proxy LiteLLM (`tech-litellm.md`);
  qui c'è solo la verifica della chiave alla registrazione e alla sostituzione, diretta presso il fornitore perché
  LiteLLM non offre un controllo gratuito (ADR 0029, ADR 0103).
- `<Fornitore>ProviderKeyVerifierAdapter` realizza `ProviderKeyVerifierPort` interrogando un endpoint gratuito che
  richiede una chiave valida: 200 accettata, 401/403 `ProviderRejectedKeyError`, ogni altra risposta o errore di rete
  `ProviderUnavailableError`. Né la chiave né la risposta del fornitore finiscono in un errore o in un log: l'errore
  di rete si scarta (`from None`) perché porta la richiesta con la chiave negli header.
- `composition.py` espone `<fornitore>_adapters()`, che restituisce `{nome del fornitore: adapter}` con il proprio
  client `httpx`; `configuration.py` la dataclass privata `_<Fornitore>Settings` col timeout. `bootstrap.py` unisce i
  dizionari; il caso d'uso sceglie il verificatore per nome e, se manca, solleva `ProviderNotVerifiableError`.
- Un fornitore nuovo nel proxy (`deploy/litellm/config.yaml`) richiede la sua cartella: un test confronta le rotte del
  proxy con le cartelle che verificano le chiavi.
