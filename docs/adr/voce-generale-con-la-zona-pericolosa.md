# ADR voce-generale-con-la-zona-pericolosa — La chiusura di emergenza di tutti i flussi nella voce «Generale»

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 563, Task 564; R3.2.3 (chiusura di emergenza)
- Collegate: `.claude/rules/tech-dashboard.md` §Pagine di impostazioni, ADR 0119 (bulletproof-react)
- Verifica: prova

## Contesto e problema

La pagina «I tuoi flussi» (`app/routes/app/home.tsx:15-17`) termina con `<DangerZone>` e la chiusura di emergenza di
tutti i flussi: un comando distruttivo in vista nella pagina d'uso quotidiano. Il proprietario (17/11/2026) lo vuole
nascosto come in GitHub o Azure DevOps, in una voce «Generale» sotto IMPOSTAZIONI del menu: impostazioni generali,
non dell'utente, e non una voce «Impostazioni» dentro la sezione Impostazioni.

## Fattori decisionali

- Decisione del proprietario (17/11/2026), Bug 563.
- Il gruppo «Impostazioni» esiste già in `NAVIGATION` (`components/layouts/dashboard-layout.tsx:23-42`: Chiavi,
  Notifiche).
- Componenti condivisi: `DangerZone`, `EmergencyClosingCommand` con `scope: { kind: 'all' }` (conferma già presente).

## Decisione

- Nuovo percorso `paths.generalSettings` (`/settings/general`) e rotta `app/routes/app/general-settings.tsx` con titolo
  «Generale» e, in fondo, `<DangerZone>` con `EmergencyClosingCommand` di tutti i flussi. Voce «Generale» prima di
  Chiavi nel gruppo Impostazioni.
- `home.tsx` perde la zona di emergenza; le zone del conto e del singolo flusso restano dove sono (il flusso le sposta
  con il Bug 560).
- Prove: la home non mostra più il comando; la pagina Generale lo mostra con la conferma; il menu ha la voce.

## Alternative scartate

- Lasciare il comando nella home dentro un riquadro chiuso: resta nella pagina d'uso quotidiano.

## Conseguenze

- «Generale» ospiterà le impostazioni generali future.
