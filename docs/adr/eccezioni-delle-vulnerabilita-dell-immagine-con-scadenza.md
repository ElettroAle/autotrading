# ADR eccezioni-delle-vulnerabilita-dell-immagine-con-scadenza — Vulnerabilità dell'immagine in attesa della base accettate con motivo e scadenza

- Stato: proposta (25 novembre 2026)
- Requisiti: Bug 736, Task 737; F0.5 (integrazione e rilascio)
- Collegate: ADR 0006 (immagine base Chainguard Python), ADR eccezioni-delle-vulnerabilita-npm-con-scadenza,
  `.claude/rules/ci.md`, `.github/actions/trivy-scan/action.yml`
- Verifica: prova

## Contesto e problema

Il job `quality / vulnerabilità` esegue Trivy sull'immagine: qualunque vulnerabilità blocca. CVE-2026-124317 e
CVE-2026-128241 (libexpat 2.10.0) sono corrette in Wolfi dalla 2.11.0, ma l'immagine base Chainguard Python più
recente contiene ancora la 2.10.0: nessun digest corretto esiste finché Chainguard non la ricostruisce, e il controllo
blocca ogni PR.

## Fattori decisionali

- Decisione del proprietario (25 novembre 2026, in chat): come per la vulnerabilità npm, esclusione solo temporanea.
- Una vulnerabilità nuova resta sempre bloccante; un'eccezione dura poco e si rivede alla scadenza (stessa regola
  dell'ADR eccezioni-delle-vulnerabilita-npm-con-scadenza).

## Decisione

- Le eccezioni stanno in `.trivyignore` alla radice, formato nativo di Trivy: per ogni vulnerabilità un commento
  «# Aggiunta il AAAA-MM-GG.» con il motivo, poi `<id> exp:AAAA-MM-GG` con la scadenza al più 14 giorni dopo.
  Trivy applica da sé la scadenza: dopo quella data la vulnerabilità torna bloccante.
- L'azione `trivy-scan` passa `--ignorefile .trivyignore`, per la qualità e per il rilascio.
- Alla scadenza o appena l'immagine base contiene la correzione: si aggiorna il digest e si toglie la voce, oppure si
  rinnova con una nuova scadenza in una PR.
- Prova: test in `tests/architecture` che verifica che ogni voce abbia il commento datato con il motivo e una
  scadenza al più 14 giorni dopo, e che l'azione legga il file.

## Alternative scartate

- Attendere la ricostruzione dell'immagine base: nessuna PR si integrerebbe nel frattempo.
- Copiare la libreria corretta dallo stadio di build nell'immagine finale: il database dei pacchetti resterebbe
  quello della base, e l'immagine smetterebbe di essere quella pubblicata da Chainguard.
- Eccezione senza scadenza: la correzione potrebbe non essere mai ripresa.

## Conseguenze

- Ogni 14 giorni un'eccezione aperta richiede una scelta esplicita.
