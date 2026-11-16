# ADR viste-e-comandi-della-pagina-del-flusso — Viste e comandi riconoscibili nella pagina del flusso

- Stato: proposta (15 novembre 2026)
- Requisiti: R6.4.1 (412), Task T6.4.1.2 (414)
- Collegate: ADR 0116 (struttura della dashboard), R2.3.10 (avviso della rete di test), R2.3.4 (comandi del flusso)

## Contesto e problema

Nella pagina del flusso cinque collegamenti di testo blu in riga mescolano viste (posizioni aperte e chiuse, cicli,
versioni) e un'azione (modifica): su un telefono non sembrano comandi e sono piccoli da toccare. I comandi Duplica,
Esporta, Avvia e Archivia hanno tutti lo stesso aspetto. La configurazione viene prima di stato e risultati; il
titolo della pagina è il generico «Flusso»; l'avviso dice «rete di test testnet» (analisi UI/UX del 15/11/2026).

## Fattori decisionali

- R6.4.1 e decisione del proprietario (15/11/2026): il disegno attuale resta, si migliorano solo i punti non
  ottimizzati.
- Elementi esistenti da riusare: `src/components/ui/view-tabs.tsx` (schede di «I tuoi flussi» e dello storico), lo
  stile del pulsante principale («Nuovo flusso») e del pulsante distruttivo («Rimuovi» dei conti).
- R2.3.10: l'avviso nomina la rete dichiarata dall'exchange.

## Opzioni considerate

1. Riusare gli elementi esistenti: viste come collegamenti con l'aspetto delle schede o dei pulsanti già in uso, aree
   toccabili di almeno 44 pixel; Modifica tra i comandi; Avvia con lo stile del pulsante principale e Archivia con
   quello distruttivo; titolo col nome del flusso, stato e avviso subito sotto, configurazione dopo i comandi.
2. Ridisegnare la pagina a schede con i contenuti caricati nella stessa pagina: scartata, cambia il disegno e le
   rotte esistenti.

## Esito della decisione

Opzione 1. Le viste restano rotte proprie (nessuna rotta nuova); i collegamenti diventano una barra di viste
riconoscibile, con l'aspetto esistente di schede o pulsanti e aree toccabili di almeno 44 pixel. Modifica la
configurazione passa tra i comandi del flusso; Avvia (o Riprendi) usa lo stile principale, Archivia quello
distruttivo. Il titolo della pagina è il nome del flusso; lo stato e l'avviso della rete vengono prima di viste,
comandi e configurazione. L'avviso cita il nome della rete tra virgolette («Il flusso opererà sulla rete di test
"testnet", senza denaro reale»), coerente con gli scenari di R2.3.10. Su schermi larghi l'impaginazione resta.

Verifica: prova (scenari di R6.4.1 e unit test dei componenti toccati; gli scenari esistenti di E2 restano verdi).

### Conseguenze

- Su un telefono si capisce dove porta ogni collegamento e quale comando è principale o distruttivo.
- I passi degli scenari di E2 che cercano i collegamenti per nome restano validi, perché i nomi accessibili non
  cambiano.
