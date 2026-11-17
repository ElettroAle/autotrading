# ADR periodi-brevi-nei-testi-dei-requisiti — Requisiti che elencano i periodi allineati ai periodi brevi

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.6 (Task 540)
- Collegate: ADR periodi-brevi-come-durata-nel-dominio, ADR periodi-brevi-nel-selettore-condiviso,
  `.claude/rules/specs.md`

## Contesto e problema

R2.2.6 (statistiche), R2.4.2 (classifica) e R6.4.3 (pagina a schede) elencano i periodi disponibili, e lo stesso fanno
R2.2.3 (equity curve) e R2.4.3 (equity sovrapposte), dove li nominano. Con R6.4.6 quegli elenchi diventano incompleti.

## Fattori decisionali

- `.claude/rules/specs.md`: i `.feature` sono la fonte di verità del COSA. Dopo una modifica si riallinea la User
  Story sulla board.
- R6.4.6: «Aggiorna i testi di R2.2.6 e R2.4.2, che elencano i periodi».

## Opzioni considerate

1. **Allineare ogni `.feature` che elenca i periodi.**
   - Nelle narrative si scrive l'elenco completo nell'ordine del menu, oppure si rimanda a R6.4.6.
   - Gli scenari esistenti non cambiano, perché provano periodi che restano validi.
   - Ogni file si valida con il parser Gherkin.
   - Le User Story corrispondenti si riallineano sulla board con lo script di sincronizzazione.
2. **Lasciare gli elenchi vecchi e citare solo R6.4.6**: scartata, perché i requisiti si contraddirebbero.

## Esito della decisione

Opzione 1.

Verifica: revisione (parser Gherkin sui file cambiati; confronto della board con i file).

### Conseguenze

- Nessun codice.
