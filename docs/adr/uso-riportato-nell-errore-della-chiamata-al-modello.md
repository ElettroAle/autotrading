# ADR uso-riportato-nell-errore-della-chiamata-al-modello — L'errore della chiamata al modello porta l'uso riportato

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 541 (Task 542), R1.4.5, R1.4.6
- Collegate: ADR 0038, ADR 0109, ADR 0027, ADR permanenza-decisa-dall-errore-base

## Contesto e problema

R1.4.6 chiede token e costo «per ogni chiamata al modello». Gli adapter OpenRouter e LiteLLM, quando il fornitore
risponde con `usage` ma senza un testo utilizzabile (per esempio `content` nullo di un modello che ragiona e consuma
tutti i `max_tokens`), sollevano `ModelUnavailableError` e l'uso riportato si perde. Lo stesso accade quando
`AgentResponse.read` rifiuta il testo in `AskAgentUseCase`: il costo della chiamata non arriva al ciclo. In dev, il
16 novembre 2026, due cicli falliti con «risposta del fornitore inattesa» sono stati addebitati da OpenRouter
(circa 0,0054 USD) e registrati senza costo.

## Fattori decisionali

- CLAUDE.md: solo errori tipizzati del progetto; l'errore dichiara la propria risposta e porta i suoi dati; le
  eccezioni delle librerie si traducono nell'adapter nell'errore del contratto della porta.
- Il caso d'uso orchestra, l'adapter traduce: nessuna decisione sul ciclo negli adapter.
- R1.4.6 «per ogni chiamata»; R1.4.5 conserva il costo di una risposta scartata.

## Decisione

- `ModelUnavailableError` (`application/agent/errors.py`) riceve due dati facoltativi: `usage: ModelUsage | None`,
  l'uso che il fornitore ha riportato, e `sent: bool`, vero quando la richiesta è partita e il fornitore può averla
  addebitata (tempo scaduto, errore HTTP dopo l'invio, risposta inutilizzabile). Status e permanenza non cambiano.
- Gli adapter `openrouter/model_call.py` e `litellm/model_call.py`, se il documento di risposta ha `usage` leggibile
  ma il testo no, sollevano `ModelUnavailableError(..., usage=<uso riportato>, sent=True)`; per tempo scaduto ed
  errori dopo l'invio `sent=True` senza uso. Un rifiuto della chiave (401/403) o del credito (402) resta com'è.
- `AskAgentUseCase` traduce un rifiuto di `AgentResponse.read` in un errore del contratto che porta `usage` e il
  costo calcolato con `ModelUsage.cost_usd(prezzi)`, così il ciclo lo registra come la risposta scartata di R1.4.5.

## Alternative scartate

- **Un errore nuovo per «risposta inutilizzabile»**: un secondo tipo per lo stesso fatto (fornitore non usabile per
  questo ciclo) moltiplicherebbe le traduzioni senza cambiare la risposta.
- **Restituire una risposta vuota con l'uso**: nasconderebbe il fallimento del passo, contro il fail fast del ciclo.

## Conseguenze

- Il costo di una chiamata pagata non si perde più nel passo dell'agente; il ciclo lo legge dall'errore (ADR
  costo-della-decisione-fallita-nel-registro-del-ciclo).
- Verifica: prova. Unit test degli adapter (documento con `usage` e `content` nullo, tempo scaduto) e di
  `AskAgentUseCase` (testo non leggibile con uso e costo).
