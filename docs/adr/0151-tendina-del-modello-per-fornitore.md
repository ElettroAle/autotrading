# ADR 0151 — Tendina del modello raggruppata per fornitore con lo stato della chiave

- Stato: accettata (14 novembre 2026), decisione del proprietario
- Requisiti: R2.3.7 (Task 268)
- Collegate: ADR 0131 (modulo del flusso dai cataloghi), ADR 0146 (campi entro la larghezza), ADR 0109

## Contesto e problema

La tendina del modello mostra solo i nomi; il catalogo dell'API restituisce già i fornitori con `key_registered`, ma il
modulo non li usa e l'utente non sa quale chiave serve.

## Fattori decisionali

- ADR 0116: la dashboard non ha logica che l'API non esponga.
- `tech-dashboard.md`: bulletproof-react, nessun import tra funzionalità, componenti condivisi in `src/components`.
- ADR 0146: i campi restano entro la larghezza dello schermo.

## Opzioni considerate

### 1. `<select>` nativo con `<optgroup>` per fornitore

- Pro: accessibile e usabile da telefono col selettore del sistema; nessuna libreria.
- Contro: lo stato della chiave sta nell'etichetta del gruppo, senza stile.

### 2. Tendina personalizzata con intestazioni e badge

- Pro: stato della chiave più visibile.
- Contro: accessibilità e telefono da rifare a mano.

## Esito della decisione

Opzione 1. `ModelFields` raggruppa i modelli per `provider` in `<optgroup>` con etichetta «<fornitore> · chiave
registrata» o «<fornitore> · chiave mancante»; i modelli di un fornitore senza chiave sono `disabled`, salvo il modello
già scelto da un flusso esistente, che resta selezionato. Se il modulo ha almeno un fornitore senza chiave, sotto il
campo compare il collegamento alla pagina delle chiavi IA (`paths.providerKeys`). Il raggruppamento è una funzione pura in
`features/flow-editor/utils`. L'API non cambia.

Verifica: revisione.

### Conseguenze

- Un flusso il cui fornitore perde la chiave si apre ancora in modifica con la scelta attuale visibile.
