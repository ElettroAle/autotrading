# ADR risposte-http-registrate-per-i-fornitori-a-chiave — Prove degli adapter con chiave su risposte HTTP registrate

- Stato: proposta (19 novembre 2026)
- Requisiti: US 341 R5.1.1 (Task 342), US 345 R5.1.3 (Task 346)
- Collegate: ADR fonti-con-adapter-dichiarati, ADR credenziali-degli-adapter-delle-fonti; `.claude/rules/tests.md`
- Verifica: prova

## Contesto e problema

`tests.md` vuole un test di integrazione per ogni adapter contro la tecnologia vera. Arkham richiede una chiave e
LunarCrush una chiave a pagamento: il proprietario non ne ha fornite e non si spende denaro.

## Fattori decisionali

- Risposta del proprietario all'avvio (19/11/2026): integrazione su risposte HTTP registrate, nessuna chiave, nessuna
  spesa; gli adapter non sono attivabili finché il proprietario non inserisce una chiave.
- Nessuna libreria nuova se `httpx` basta.

## Decisione

- Gli adapter `arkham/` e `lunarcrush/` ricevono un `httpx.Client`; i test di integrazione
  (`tests/integration/sources/test_<adapter>_recorded.py`, marker `integration`) lo costruiscono con
  `httpx.MockTransport` che risponde con i JSON registrati in `tests/integration/sources/recorded/<adapter>/`, presi
  dagli esempi della documentazione ufficiale del fornitore e citati con l'URL della pagina nel test.
- Ogni test verifica anche la richiesta: URL, parametri, intestazione della chiave.
- Si registrano anche le risposte di errore (401, 429, 5xx) per provare la traduzione negli errori tipizzati.
- Un test `live` con la chiave vera, fuori dalla suite, si aggiunge quando il proprietario fornisce una chiave.

## Alternative scartate

- Libreria di registrazione (vcrpy, respx): una dipendenza in più per ciò che `MockTransport` fa già.

## Conseguenze

- Un cambio del formato del fornitore non si vede finché non c'è il test live.
