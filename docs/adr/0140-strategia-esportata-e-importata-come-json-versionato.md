# ADR 0140 — La strategia si esporta e si importa come documento JSON versionato che crea una bozza

- Stato: proposta (14 novembre 2026)
- Requisiti: R2.5.2 (Task T2.5.2.1)
- Collegate: RF-21.06; ADR 0124 (flusso in bozza), R1.1.1 (validazione della configurazione), ADR 0027 (Problem
  Details), ADR 0018 (numeri come stringhe)

## Contesto e problema

L'esportazione produce un file con la sola strategia (intervallo, fonti con pesi e parametri, modello con
parametri, istruzioni, regole di rischio), senza conto, capitale, asset, chiavi né cicli. L'importazione di un
file valido crea una bozza alla versione 1 con il nome scelto; un file non valido si rifiuta con il motivo senza
creare nulla.

## Decisione

- Value object `FlowStrategy` nel dominio `flows`: la parte della configurazione che il file porta, ricavata dalla
  configurazione corrente e validata con le stesse regole della creazione (modello nel catalogo, fonti esistenti,
  pesi, rischio).
- Casi d'uso `ExportFlowStrategyUseCase` e `ImportFlowStrategyUseCase`; l'importazione crea la bozza con la
  stessa via di ADR 0124, dopo aver validato tutto, così un errore non lascia nulla.
- Il formato del file lo dichiara l'adapter FastAPI con modelli Pydantic: `{"format": "autotrading-strategy",
  "format_version": 1, "strategy": {...}}`, numeri come stringhe; un formato o una versione sconosciuti sono un
  errore 400 col motivo.
- API: `GET /flows/{flow_id}/strategy` (download con `Content-Disposition`, nome del file dal nome del flusso) e
  `POST /flows/import` (nome del nuovo flusso e documento).

## Alternative scartate

- **Esportazione dell'intera configurazione con i campi del conto azzerati**: meno codice, ma il file porterebbe
  campi che il requisito esclude.
- **Formato senza versione**: più semplice oggi, ma nessun modo di riconoscere un file vecchio domani.

## Conseguenze

- Un campo nuovo della strategia richiede di decidere se entra nel file e di alzare `format_version` se cambia la
  forma.
