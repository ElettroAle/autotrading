# ADR opzioni-della-memoria-nella-dashboard — Riepilogo e altri asset della memoria nella dashboard

- Stato: accettata (26 novembre 2026)
- Requisiti: US 762 R5.3.7 (Task 764)
- Collegate: ADR 0116, ADR 0129 (sezioni apribili), ADR memoria-del-flusso-con-riepilogo-e-altri-asset;
  `.claude/rules/tech-dashboard.md`
- Verifica: prova

## Contesto e problema

R5.3.7 chiede gli interruttori riepilogo e altri asset nel modulo del flusso e le righe di riepilogo nella memoria
mostrata nelle decisioni.

## Fattori decisionali

- Decisioni del proprietario già scritte: la sezione «Memoria» del modulo sta subito dopo il modello; la memoria si
  consulta su richiesta nella scheda «Decisioni» (25 novembre 2026).
- Regole UI/UX del repository: ogni campo dice che cosa ammette.
- Nessuna logica di business nella dashboard (ADR 0116).

## Decisione

- Nella sezione «Memoria» del modulo, dopo «Tutte le decisioni», le caselle «Riepilogo per asset e direzione» e
  «Altri asset del flusso», ciascuna con la riga di aiuto; abilitate solo con la memoria attiva.
- Nella memoria mostrata nelle decisioni, per ogni asset, le righe di riepilogo e quelle degli altri asset prima della
  tabella delle decisioni, con il testo che l'API restituisce.

## Alternative scartate

- **Righe di riepilogo in una tabella calcolata dalla dashboard**: calcolo fuori dall'API.

## Conseguenze

- La dashboard mostra ciò che l'agente riceve.
