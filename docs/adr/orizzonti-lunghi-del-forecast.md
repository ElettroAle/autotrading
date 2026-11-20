# ADR orizzonti-lunghi-del-forecast — Orizzonti di 1 giorno e 1 settimana del forecast

- Stato: proposta (19 novembre 2026)
- Requisiti: US 349 R5.1.5, Task 350
- Collegate: ADR 0043, ADR 0107 (Prophet nel container forecaster), ADR fonti-con-adapter-dichiarati, ADR 0131;
  `.claude/rules/context-sources.md`, `.claude/rules/tech-forecaster.md`
- Verifica: prova

## Contesto e problema

R5.1.5 vuole che la fonte «forecast» accetti anche 1 giorno e 1 settimana oltre a 15 minuti e 1 ora, calcolati su
candele giornaliere, registrati e con il prezzo effettivo allo scadere; un orizzonte non ammesso è rifiutato con
il motivo che elenca gli ammessi. Oggi i parametri sono interi con minimo e massimo, senza elenco di valori.

## Fattori decisionali

- Il motivo deve elencare gli orizzonti ammessi con il loro nome.
- I parametri si generano dal catalogo nella dashboard (ADR 0131).

## Decisione

- **Parametri a scelta**: `SourceParameter` riceve `choices: tuple[ParameterChoice(value: int, label: str), ...]`
  (vuoto = intervallo come oggi); un valore fuori dalle scelte è rifiutato con «<parametro>: ammessi <etichette>».
  L'API espone `choices` e l'editor mostra una selezione.
- **Forecast**: 15 minuti e 1 ora restano sempre; nuovo parametro `orizzonte_lungo` con scelte 0 «nessuno»
  (predefinito), 1440 «1 giorno», 10080 «1 settimana». Gli orizzonti lunghi si calcolano su candele giornaliere con
  profondità `profondita_lunga_giorni` (predefinito 365, da 30 a 1000); storico più corto dichiarato come oggi.
- La previsione lunga si registra come le altre con il suo orizzonte e riceve il prezzo effettivo allo scadere dal
  meccanismo esistente; il servizio forecaster riceve candele giornaliere e l'orizzonte in giorni.

## Alternative scartate

- Orizzonte come intero in minuti libero: il motivo non saprebbe elencare gli ammessi.

## Conseguenze

- Le scelte valgono per ogni parametro futuro a valori discreti.
