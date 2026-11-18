# ADR nomi-e-istanti-dei-guadagni — «Guadagno attuale» al posto di «Guadagno totale»

- Stato: proposta (18 novembre 2026)
- Requisiti: Bug 612, Task 613; R6.4.2
- Collegate: ADR riepilogo-dei-risultati-nell-api, ADR riepilogo-dei-risultati-nella-dashboard
- Verifica: prova

## Contesto e problema

Il riepilogo del flusso mostra «Guadagno totale» (letto adesso, posizioni aperte comprese) e «Guadagno nel periodo»
(dalle equity registrate dai cicli, fino all'ultimo ciclo del periodo): anche con il periodo dall'inizio differiscono.
Il calcolo resta: il proprietario lo ha confermato ritirando il Bug 603.

## Fattori decisionali

- Decisione del proprietario (18/11/2026): «Guadagno attuale» al posto di «Guadagno totale»; nessun sottotitolo.

## Decisione

- Dashboard: l'etichetta «Guadagno totale» diventa «Guadagno attuale» ovunque compare (riepilogo del flusso, scheda del
  flusso nell'elenco, classifica se la usa); «Guadagno nel periodo» resta. Nessuna nota sotto i valori.
- Specifiche che citano «Guadagno totale» (R6.4.2 e le altre trovate con la ricerca) e board riallineate.
- Prove: unit test dei componenti e scenari che cercano l'etichetta.

## Alternative scartate

- Sottotitoli con l'istante dei due valori: scartati dal proprietario.

## Conseguenze

- Il nome dice che il valore è quello di adesso.
