# ADR 0002 — Artefatto unico promosso per digest

- Stato: accettata (8 novembre 2026)
- Requisiti: R0.5.2, R0.5.3

## Contesto

In Pipelines V3 la promozione ricompila il binario con la versione definitiva. Il proprietario
chiede che in prod arrivi l'artefatto provato in dev.

## Decisione

- L'immagine Docker del servizio si costruisce **una volta** per integrazione, si scansiona con
  Trivy e solo se pulita si pubblica su GHCR con la versione di pre-release.
- Il rilascio in dev e in prod usa sempre il riferimento **per digest** (`repository@sha256:...`).
- La promozione aggiunge il tag della versione di rilascio allo **stesso digest**
  (`docker buildx imagetools create`), senza ricostruire.
- La versione dichiarata dall'installazione arriva come configurazione al rilascio
  (`APP_VERSION`), non dentro l'immagine: lo stesso digest dichiara `1.2.1-dev.57` in dev e
  `1.2.1` in prod.
- La macchina scarica l'immagine con il token di sola lettura dell'esecuzione, rimosso con
  `docker logout` subito dopo il pull: nessuna credenziale di registro resta sulla macchina.

## Alternative scartate

- **Ricompilare alla promozione** (V3): prod riceverebbe un binario mai provato.
- **Versione dentro l'immagine**: obbligherebbe a ricostruire per cambiarla.
- **Pacchetto GHCR pubblico** per evitare il login: richiede un passo manuale dopo la prima
  pubblicazione e rende pubblico l'artefatto.

## Conseguenze

- Una run in attesa di approvazione per prod resta valida finché il suo digest esiste.
- Il rilascio in dev e quello in prod sono serializzati per ambiente (`concurrency` per job), così
  un'approvazione in sospeso non blocca i rilasci in dev successivi.
