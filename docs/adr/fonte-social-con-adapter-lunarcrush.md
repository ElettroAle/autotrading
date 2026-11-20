# ADR fonte-social-con-adapter-lunarcrush — Fonte social con l'adapter LunarCrush

- Stato: proposta (19 novembre 2026)
- Requisiti: US 345 R5.1.3, Task 346
- Collegate: ADR fonti-con-adapter-dichiarati, ADR credenziali-degli-adapter-delle-fonti, ADR
  risposte-http-registrate-per-i-fornitori-a-chiave; `.claude/rules/context-sources.md`
- Verifica: prova

## Contesto e problema

R5.1.3 vuole una fonte per asset «social» con l'adapter LunarCrush (chiave a pagamento): sentiment social, volume di
menzioni e interazioni delle ultime 24 ore e i messaggi più rilevanti dei creatori più influenti, con autore, data e
testo; numero di messaggi parametro dell'adapter (predefinito 5).

## Fattori decisionali

- Decisione del proprietario (backlog E5): LunarCrush, adapter a pagamento non attivabile senza chiave; nessuna spesa.

## Decisione

- **Domain `sources`**: fonte per asset `social`; `SocialSnapshot(sentiment, mentions_24h, interactions_24h, posts)`
  con `SocialPost(author, at, text)`; i messaggi oltre il numero richiesto si scartano nel domain.
- **Application**: porta `SocialPort` (`declaration()`, `snapshot(asset, posts, credentials)`) e lettore
  `ReadSocialUseCase` registrato per (social, adapter).
- **Adapter `adapters/outbound/lunarcrush/`** (`LunarCrushSocialAdapter`): API v4 (dati della moneta per sentiment,
  menzioni e interazioni; messaggi del topic ordinati per interazioni dei creatori), chiave come Bearer. Dichiarazione:
  nome «LunarCrush», campo segreto «chiave API», parametro proprio `numero_messaggi` (predefinito 5, da 1 a 20),
  `offers_history` falso. Prove su risposte registrate (ADR risposte-http-registrate-per-i-fornitori-a-chiave).
- `.claude/rules/tech-lunarcrush.md` e la cartella `lunarcrush/` nell'elenco degli adapter in uscita di `CLAUDE.md`.

## Alternative scartate

- X o altri fornitori: fuori ambito.

## Conseguenze

- Diventa attivabile quando il tenant inserisce la chiave.
