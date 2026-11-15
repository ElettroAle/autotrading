# ADR ritocchi-delle-pagine-della-dashboard — Ritocchi mirati delle altre pagine della dashboard

- Stato: proposta (15 novembre 2026)
- Requisiti: R6.4.1 (412), Task T6.4.1.3 (415)
- Collegate: ADR 0116 (struttura della dashboard), R2.5.1 (storico), R1.8.1 (collegamento Telegram), R2.3.7
  (versioni della configurazione)

## Contesto e problema

L'analisi UI/UX del 15/11/2026 a 360 pixel ha trovato punti non ottimizzati fuori dalla pagina del flusso: le
sottopagine di un flusso (cicli, posizioni aperte e chiuse, versioni, modifica) non dicono di quale flusso sono;
nello storico i filtri sono in riga e ogni etichetta finisce a destra del campo precedente; la pagina Notifiche non
spiega come collegare Telegram; il confronto delle versioni è attivo con una sola versione; gli esiti dei cicli
recenti nell'elenco dei flussi non hanno legenda.

## Fattori decisionali

- R6.4.1 e decisione del proprietario (15/11/2026): ritocchi mirati, il disegno attuale resta.
- `.claude/rules/tech-dashboard.md`: la dashboard mostra solo dati che l'API espone; il nome del flusso è già nella
  risposta del flusso.
- Il bot Telegram collega la chat con il codice di collegamento (R1.8.1).

## Opzioni considerate

1. Ritocchi puntuali nei componenti esistenti.
2. Un'intestazione comune con percorso di navigazione per tutte le pagine: scartata, cambia il disegno.

## Esito della decisione

Opzione 1:

- le sottopagine di un flusso mostrano il nome del flusso nel titolo o subito sotto (per esempio «Cicli di
  prova-btc»), letto dalla stessa API del flusso;
- i filtri dello storico si impilano su schermi stretti con l'etichetta sopra il proprio campo, in riga su schermi
  larghi;
- la pagina Notifiche, senza chat collegata, elenca i passi del collegamento (chiedere il codice, inviarlo al bot,
  attendere la conferma), con il testo coerente con le risposte del bot;
- Confronta è disattivato finché il flusso ha una sola versione;
- gli esiti dei cicli recenti hanno una legenda visibile (concluso, fallito) oltre ai nomi accessibili esistenti.

Verifica: prova (scenari di R6.4.1 e unit test dei componenti toccati; gli scenari esistenti di E2 restano verdi).

### Conseguenze

- Ogni sottopagina dice a quale flusso appartiene e i filtri dello storico si leggono su un telefono.
