# ADR perdita-massima-sui-valori-di-equity-registrati — Perdita massima del flusso sui valori di equity registrati

- Stato: proposta (16 novembre 2026)
- Requisiti: R3.2.2 (459), Task T3.2.2.1 (480)
- Collegate: ADR 0040 (controllo del rischio), ADR 0120 (l'equity di ogni ciclo si registra), ADR 0035
  (collegamento di Telegram e notifiche), ADR 0027 (errori che dichiarano la risposta), ADR 0051 (porta al minimo
  nella configurazione)

## Contesto e problema

Un flusso deve smettere di aprire posizioni quando perde oltre una soglia giornaliera (rispetto al valore delle
00:00 UTC) o dal picco (rispetto al valore più alto dall'avvio o dall'ultima ripresa delle aperture). Le variazioni
di capitale non sono perdite né guadagni. La sospensione blocca solo le aperture, avvisa una volta e riprende per
comando dell'utente ("manuale", predefinita) o da sola alle 00:00 UTC del giorno dopo ("il giorno dopo").

## Fattori decisionali

- R3.2.2 e decisione del proprietario sull'intervista di E3: soglie giornaliera (UTC) e dal picco, ripresa
  "manuale" o "il giorno dopo" scelta per flusso.
- ADR 0120: ogni ciclo registra l'equity del flusso con le sue parti, compreso il capitale allocato del momento.
- R1.1.3 e Bug 441: soglie e ripresa versionate e visibili nel confronto delle versioni.
- Il ciclo continua: chiusure e aggiornamenti del piano di uscita si eseguono (R3.1.2).
- Nessuna logica di business nella dashboard (ADR 0116): lo stato della sospensione lo calcola l'API.

## Opzioni considerate

1. **Valori di riferimento ricavati dalle equity registrate, sospensione salvata sul flusso.**
   - Riferimento giornaliero: l'ultima equity registrata alle 00:00 UTC di oggi o prima (la prima di oggi se il
     flusso non ne ha prima); picco: la più alta registrata da `max(first_started_at, ripresa delle aperture)`,
     comprendendo il valore letto ora. Ogni valore registrato si porta al capitale di oggi: equity del punto − suo
     capitale allocato + capitale allocato attuale, così aumenti, riduzioni e incassi spostano i riferimenti dello
     stesso importo senza scritture.
   - Sospensione: colonne nuove su `flows` (motivo, istante della sospensione, istante dell'ultima ripresa delle
     aperture), con migrazione; restano sotto la RLS del tenant.
2. Riferimenti salvati e aggiornati a ogni ciclo e a ogni variazione di capitale: scartata, duplica le equity e
   richiede di spostarli in ogni caso d'uso del capitale.
3. Un lavoro pianificato alle 00:00 UTC per la ripresa "il giorno dopo": scartato, la regola si valuta all'istante
   in cui serve (ciclo, lettura, comando) senza un altro lavoro nel pianificatore.

## Esito della decisione

Opzione 1.

- Domain (`flows`): in `FlowConfiguration` `max_daily_loss_percent` e `max_drawdown_percent` (facoltativi, da 0,1
  a 100, errore tipizzato "la perdita massima va da 0,1 a 100") e `openings_resume` (`OpeningsResume`: manuale,
  predefinita; il giorno dopo); voci `FlowSetting` e parti del confronto delle versioni ("perdita giornaliera
  massima", "perdita massima dal picco", "ripresa delle aperture"). Un tipo `LossGuard` puro calcola, da valore
  attuale, riferimenti e soglie, il motivo ("perdita giornaliera 6% oltre il 5%", "perdita dal picco 11% oltre il
  10%"; la giornaliera prima se entrambe superate); `OpeningsSuspension` dice se la sospensione è in vigore a un
  istante: con ripresa "il giorno dopo" finisce alle 00:00 UTC del giorno dopo la sospensione, e quell'istante è la
  ripresa da cui riparte il picco.
- Ciclo: nel passo del rischio, prima di `CheckRiskUseCase`, un caso d'uso `GuardFlowLossUseCase` legge
  sospensione e riferimenti (porte nuove in `application/flows/ports.py`, realizzate dall'adapter `sqlalchemy`),
  applica la ripresa "il giorno dopo" scaduta, valuta le soglie e, solo al passaggio da non sospeso a sospeso,
  salva la sospensione e avvisa "alfa: aperture sospese, <motivo>" attraverso una porta realizzata da un caso
  d'uso di `notifications` (come la notifica di pausa). `RiskState` porta la sospensione: `RiskCheck` blocca ogni
  apertura con "aperture sospese per perdita massima" e lascia passare chiusure e mantenimenti.
- Ripresa: `ResumeFlowOpeningsUseCase` toglie la sospensione e segna la ripresa ora; senza sospensione in vigore
  solleva un errore tipizzato "le aperture di <flusso> non sono sospese" (409). Rotta `POST
  /flows/{flow_id}/openings/resume`; dettaglio ed elenco dei flussi riportano la sospensione in vigore (motivo e
  istante) o `null`.
- Configurazione nel documento JSON della versione con chiavi `NotRequired` (assenti = nessuna soglia, ripresa
  manuale), nelle richieste e risposte dell'API, nel documento della strategia e nel client OpenAPI rigenerato.

Verifica: prova (scenari di R3.2.2 con adapter finti, unit test di `LossGuard`, `OpeningsSuspension`, casi d'uso e
`RiskCheck`, test di integrazione dei riferimenti e della sospensione sull'adapter `sqlalchemy` con la RLS).

### Conseguenze

- Le soglie si valutano al passo del rischio di ogni ciclo: una perdita tra due cicli si vede al ciclo successivo.
- La ripresa "il giorno dopo" non dipende da un lavoro pianificato: la vede subito chi legge il flusso.
- Un flusso senza equity registrate (primo ciclo) non ha riferimenti e non si sospende.
