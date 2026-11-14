# ADR 0156 — Pagina dei flussi con azioni in testata, importazione su richiesta e vista classifica

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.1.3 (Task 276)
- Collegate: ADR 0155 (menu a gruppi), ADR 0119, ADR 0146 (campi entro la larghezza)

## Contesto e problema

La pagina dei flussi mostra in sequenza i collegamenti ad altre aree, il pulsante «Nuovo flusso», l'elenco, il modulo
di importazione sempre aperto e la classifica come collegamento in fondo. Con il menu a gruppi (ADR 0155) i
collegamenti ad altre aree escono; restano le azioni e le viste dei flussi.

## Fattori decisionali

- Decisione del proprietario (14 novembre 2026, R2.1.3): nuovo flusso, importazione e classifica nella pagina dei
  flussi; importazione su richiesta.
- `tech-dashboard.md`: componenti condivisi in `src/components`, nessun import tra funzionalità.
- La classifica ha già il suo indirizzo (`/ranking`), da cui si apre il confronto.

## Opzioni considerate

### 1. Schede come collegamenti tra `/` e `/ranking`, importazione in un pannello che si apre

- Pro: indirizzi invariati e condivisibili; il pulsante Indietro funziona tra le viste; il pannello rispetta la
  larghezza del telefono.
- Contro: la scheda vive in due pagine.

### 2. Classifica caricata nella stessa pagina con stato locale

- Pro: nessun cambio di pagina.
- Contro: la classifica perde l'indirizzo proprio e il ritorno dal confronto.

## Esito della decisione

Opzione 1. Un componente condiviso `ViewTabs` in `src/components/ui` (barra di collegamenti con `aria-current="page"`
sulla vista attiva) mostra «Elenco» (`/`) e «Classifica» (`/ranking`) in testa alle due pagine. La testata della pagina
dei flussi ha «Nuovo flusso» e «Importa»; «Importa» è un pulsante con `aria-expanded` che apre e chiude il modulo di
importazione esistente. Escono dalla pagina i collegamenti a conti, storico, chiavi e notifiche. Il titolo della
classifica diventa «I tuoi flussi», come l'elenco, perché è una vista della stessa area.

Verifica: revisione.

### Conseguenze

- Una nuova vista dei flussi si aggiunge come scheda con il suo indirizzo.
