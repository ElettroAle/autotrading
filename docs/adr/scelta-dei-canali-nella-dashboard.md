# ADR scelta-dei-canali-nella-dashboard — Scelta dei canali nella dashboard

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.5.3 (469), Task T3.5.3.2 (495)
- Collegate: ADR canali-delle-notifiche-per-tipo-di-evento, ADR indirizzo-email-nelle-impostazioni-delle-notifiche,
  ADR tabella-condivisa-senza-sforamento-e-con-filtri

## Contesto e problema

La pagina Notifiche deve mostrare per ogni tipo di evento il canale scelto, permettere di cambiarlo, gestire le
eccezioni di un flusso e mostrare l'avviso del canale non collegato.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): regole architetturali del contratto e componenti riusabili dove possibile
  (tabella condivisa, schede `ViewTabs`, campi di `src/components/ui`), nessun duplicato per pagina.
- `.claude/rules/tech-dashboard.md`; l'API restituisce tipi di evento, nomi, canali e avvisi già calcolati.

## Opzioni considerate

1. Nella funzionalità `notifications`: sezione «Canali per tipo di evento» con la tabella condivisa (colonne tipo di
   evento, canale come selettore, avviso); sotto, la scelta di un flusso e la stessa tabella per le sue eccezioni
   (canale «come la scelta generale» per togliere l'eccezione; gli eventi del conto non compaiono).
2. Un selettore per evento in un form libero: scartato, non riusa la tabella condivisa e non regge su telefono.

## Esito della decisione

Opzione 1.

Verifica: prova (unit test della sezione con API finta; scenari di R3.5.3 con pytest-bdd).

### Conseguenze

- Ogni tipo di evento nuovo compare da solo, perché la lista viene dall'API.
