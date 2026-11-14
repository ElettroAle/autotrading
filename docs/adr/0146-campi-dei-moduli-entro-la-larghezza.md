# ADR 0146 — I campi dei moduli restano dentro la larghezza del modulo

- Stato: accettata (14 novembre 2026), approvata dal proprietario
- Requisiti: Bug 261 (Task 264)
- Collegate: ADR 0116, ADR 0131 (editor del flusso), R2.1.2 (uso da telefono)

## Contesto e problema

Nel modulo del flusso la tendina del modello si allarga quanto il nome di modello più lungo del catalogo ed esce dallo
schermo del telefono. Le classi dei campi sono ripetute per file (`const INPUT` in `flow-form.tsx`, `model-fields.tsx`,
`source-fields.tsx`) senza un vincolo di larghezza.

## Decisione

- Una sola definizione condivisa dello stile dei campi (componenti o classi in `src/components/ui`), usata da tutti i
  moduli: larghezza piena del modulo (`w-full`), mai oltre (`max-w-full`, `min-w-0` nei contenitori flessibili), testo
  troncato nel campo chiuso.
- Le copie locali di `INPUT` si eliminano.
- Una prova Playwright a larghezza telefono verifica che nessun campo del modulo del flusso superi la larghezza della pagina.

## Alternative scartate

- **Correggere solo la tendina del modello**: veloce, ma il prossimo campo con valori lunghi ripete il difetto.
- **Nomi dei modelli accorciati nella dashboard**: logica di presentazione sui dati del catalogo, e nomi ambigui.

## Conseguenze

- Tutti i moduli condividono lo stesso comportamento sugli schermi stretti.
