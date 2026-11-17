# ADR prove-dell-accesso-che-dura — Prove dell'accesso che dura con l'identity provider finto

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.1 (Task 513)
- Collegate: ADR accesso-persistente-con-cache-msal-in-localstorage, ADR content-security-policy-rigida-della-dashboard,
  `.claude/rules/tech-dashboard.md` §Prove

## Contesto e problema

Gli scenari di R6.5.1 dipendono da due stati dell'identity provider:
- la sessione Entra viva o finita;
- il refresh token valido o scaduto.

Dipendono anche da ciò che resta nel browser tra due aperture. Oggi i finti MSW di `src/testing/mocks` modellano un
accesso sempre valido.

## Fattori decisionali

- `.claude/rules/tech-dashboard.md` §Prove: scenari con `playwright-bdd` sulla build servita da `server/`, browser
  instradato ai finti MSW, MSAL vero; ogni `Allora` e ogni `E` con la propria asserzione.
- Direttiva del proprietario sui componenti riusabili: lo stato dell'IdP finto sta nella piattaforma finta condivisa
  (`fakePlatform`), non nei passi di un solo requisito.

## Opzioni considerate

1. **IdP finto con stato di sessione.**
   - L'endpoint di autorizzazione finto risponde senza la pagina delle credenziali quando la sessione finta è viva,
     e con la pagina delle credenziali quando è finita.
   - L'endpoint del token rifiuta il refresh token marcato scaduto con `invalid_grant`.
   - «Riapertura dopo la chiusura del browser»: un nuovo contesto Playwright con lo `storageState` del primo (cioè
     `localStorage`) e la sessione finta ancora viva.
   - «Esci»: si verifica che `localStorage` e `sessionStorage` siano vuoti e che la riapertura mostri le credenziali.
   - «Content Security Policy rigida»: si legge l'intestazione della risposta e si registra ogni
     `securitypolicyviolation`.
2. **Prove contro Entra vero**: scartata, perché servirebbero credenziali nella pipeline. Entra vero si verifica a
   mano su dev dopo il rilascio.

## Esito della decisione

Opzione 1. `dashboard/playwright.config.ts` e la rule elencano `specs/E6-*/F6.5-*`.

Verifica: prova (scenari di R6.5.1 al 100%, unit test dei finti estesi).

### Conseguenze

- Gli altri scenari della dashboard partono con la sessione finta viva: comportamento invariato.
