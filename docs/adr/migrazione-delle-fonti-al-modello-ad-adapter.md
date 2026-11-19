# ADR migrazione-delle-fonti-al-modello-ad-adapter — Configurazioni dei flussi al modello ad adapter con una nuova versione

- Stato: proposta (19 novembre 2026)
- Requisiti: US 310 R4.1.1, Task 312; dipende dal Task 311
- Collegate: ADR fonti-con-adapter-dichiarati, ADR 0133 (versioni della configurazione), ADR 0140 (strategia
  esportata); migrazioni `0029_protection_defaults.py`, `0031_minimum_confidence.py`; `.claude/rules/tech-sqlalchemy.md`
- Verifica: prova

## Contesto e problema

Le configurazioni dei flussi stanno in `flow_versions` (append-only, una riga per versione, documento JSON con
`sources: [{name, weight, parameters}]`). R4.1.1 vuole che le configurazioni esistenti passino al modello ad adapter
conservando pesi e parametri, con una nuova versione. Le migrazioni precedenti (0029, 0031) aggiornavano le righe sul
posto senza versione nuova: questa è la prima che ne crea una.

## Fattori decisionali

- R4.1.1: «nuova versione della configurazione», pesi e parametri invariati.
- Le versioni sono storia append-only (ADR 0133): una versione passata non si riscrive.
- Le versioni passate restano consultabili, confrontabili e ripristinabili.
- I nomi dei fornitori stanno solo negli adapter (la migrazione e il repository sono nell'adapter SQLAlchemy).

## Decisione

- **Corrispondenza** (una sola, nell'adapter SQLAlchemy, usata da migrazione e lettura): `sentiment-alternative-me`
  → fonte `sentiment`, adapter «alternative.me»; `sentiment-coinmarketcap` → fonte `sentiment`, adapter
  «CoinMarketCap» (se ci sono entrambe, una sola fonte con i due adapter nell'ordine originale); `indicatori`,
  `pivot`, `forecast`, `notizie` → la stessa fonte con il suo unico adapter, col nome della dichiarazione dell'adapter
  (ADR fonti-con-adapter-dichiarati). Peso e parametri passano all'adapter invariati.
- **Migrazione Alembic `0050`** (numero successivo all'ultimo su main al momento dello sviluppo): per ogni flusso, se
  l'ultima versione ha il formato vecchio, inserisce una versione `ultima + 1` con il documento convertito e
  `created_at` all'istante della migrazione, con la RLS sospesa come 0029 (`NO FORCE` / `FORCE ROW LEVEL SECURITY`). La
  stessa conversione per la strategia del flusso se è salvata in un documento proprio. Le versioni precedenti restano
  intatte. Il `downgrade` elimina le versioni create dalla migrazione, riconosciute da un marcatore nel documento
  (`"migrated_from": "sources-v1"`) che il repository ignora.
- **Lettura delle versioni passate**: il repository riconosce il formato vecchio (`sources[].name` senza `adapters`) e
  lo converte in memoria con la stessa corrispondenza, così storia, differenze (`configuration_difference`) e
  ripristino producono sempre il modello nuovo; ripristinare una versione vecchia crea una versione nel modello nuovo.
- **Campioni**: `source_samples` riceve la colonna `adapter` (testo); la migrazione la riempie con la stessa
  corrispondenza e rinomina `source` dei sentiment in `sentiment`.
- **Il proprietario vede la nuova versione** nella cronologia del flusso con la differenza delle fonti; nessuna
  notifica.

## Alternative scartate

- Aggiornare le righe sul posto come 0029: niente nuova versione, contro R4.1.1, e riscrive la storia.
- Convertire solo in lettura senza migrazione: nessuna nuova versione, e due formati vivi nel database per sempre.

## Conseguenze

- Un ciclo in corso durante il rilascio termina con la configurazione che aveva letto; il ciclo successivo legge la
  versione nuova.
- Il marcatore resta nei documenti migrati come traccia dell'origine.
