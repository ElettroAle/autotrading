# ADR periodi-brevi-nel-selettore-condiviso — Periodi brevi nel selettore condiviso e grafico con zero o un punto

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.4.6 (Task 539)
- Collegate: ADR periodi-brevi-come-durata-nel-dominio, ADR periodo-al-minuto, ADR 0121 (grafici condivisi), ADR
  pagina-del-flusso-a-schede-sotto-un-periodo-comune, ADR 0116

## Contesto e problema

Il selettore condiviso `src/components/ui/period-selector` ha `PERIODS` (Tutta la vita, 7 giorni, 30 giorni,
Intervallo) e calcola in giorni (`LAST_DAYS`) la finestra delle liste che l'API filtra con `from`/`to`. Con 30 minuti
o 1 ora l'equity curve può avere un solo punto o nessuno.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): ordine dal più breve, predefinito «Tutta la vita».
- Direttiva del proprietario (16/11/2026): componenti riusabili. Il selettore condiviso è l'unico punto dei periodi.
  Lo stato vuoto e il punto singolo stanno nel grafico condiviso di `src/components/charts`, non nelle pagine.
- `.claude/rules/tech-dashboard.md`: periodo nell'indirizzo; nessuna logica di business. La finestra delle liste
  replica la durata dell'API (`7d` vale 7 giorni da adesso); l'API resta la fonte per i pannelli che ricevono
  `period`.

## Opzioni considerate

1. **`PERIODS` in ordine e durate in millisecondi.**
   - `PERIODS`: `30m` «30 minuti», `1h` «1 ora», `12h` «12 ore», `24h` «24 ore», `7d`, `30d`, `all`, `range`.
     «Tutta la vita» resta il predefinito e non lascia traccia nell'indirizzo.
   - `LAST_DAYS` diventa `LAST_DURATIONS_MS` per i sei periodi «ultimi N». Le liste ricevono `from` uguale ad
     adesso meno la durata, al minuto UTC.
   - Il grafico condiviso dell'equity mostra il solo punto come marcatore visibile quando i dati sono uno, e «nessun
     ciclo nel periodo» quando sono zero.
   - Le statistiche mostrano «nessuna operazione nel periodo» quando non ci sono operazioni nel periodo.
   - I finti MSW (`windowOf`, `intervalWindowOf`) accettano i periodi nuovi.
2. **Menu a due livelli (ore e giorni)**: scartata, perché il proprietario ha chiesto un solo elenco in ordine.

## Esito della decisione

Opzione 1.

Verifica: prova.
- Unit test di `use-period` (ordine, indirizzo, finestra di ogni periodo) e del grafico con zero o un punto.
- Scenari Playwright di R6.4.6.

### Conseguenze

- Le pagine che usano il selettore (flusso, classifica, storico, confronto) ricevono i periodi nuovi senza modifiche
  proprie.
