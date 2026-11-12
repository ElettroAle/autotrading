# ADR 0051 — Opzione "porta al minimo" nella configurazione del flusso

- Stato: accettata (12 novembre 2026)
- Requisiti: R1.5.4 (Task T1.5.4.1)

## Contesto

La regola dell'importo minimo con l'opzione "porta al minimo" è nel domain di `flows` (ADR 0040), ma l'opzione
non esiste ancora nella configurazione del flusso né nella sua API: il requisito la vuole disattivata per
impostazione predefinita. La configurazione è salvata come documento JSON per versione (`flow_versions`), e la
modifica versionata della configurazione (R1.1.3) è in sviluppo in parallelo.

## Opzioni considerate

### 1. Campo `bring_to_minimum` della configurazione, nel documento JSON della versione

- Pro: nessuna migrazione; le versioni salvate senza il campo si leggono con l'opzione disattivata; la politica
  del rischio si ricava dalla configurazione in un solo punto.
- Contro: nessuno rilevante.

### 2. Colonna dedicata nella tabella dei flussi

- Pro: interrogabile da SQL.
- Contro: l'opzione cambierebbe senza nuova versione, contro R1.1.3.

## Esito della decisione

Scelta: **opzione 1**. `FlowConfiguration.bring_to_minimum` (falso per impostazione predefinita) e la proprietà
`risk_policy`, che dà `RiskPolicy(limiti, porta al minimo)`. L'API di creazione accetta `bring_to_minimum`
(facoltativo, falso) e la risposta lo riporta; il documento della versione lo salva, e una versione senza il campo
si legge con l'opzione disattivata.

### Conseguenze

- La modifica della configurazione (R1.1.3) riporta il campo nella nuova versione come ogni altro.
- Il ponte del rischio nel ciclo legge la politica da `configuration.risk_policy`.
