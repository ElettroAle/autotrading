# ADR accesso-persistente-con-cache-msal-in-localstorage — Accesso che dura: cache MSAL in localStorage e rinnovo per redirect

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.1 (Task 511)
- Supera: ADR 0118 nella sola parte «cache dei token in `sessionStorage`» e nel ritorno alla pagina di accesso a ogni
  sessione scaduta. Restano valide le altre parti della 0118: PKCE, client pubblico, MSAL in `src/lib`, autorizzazione
  sull'API, issuer generico.
- Collegate: ADR 0116, ADR 0117, ADR content-security-policy-rigida-della-dashboard, `.claude/rules/tech-dashboard.md`
  §Accesso

## Contesto e problema

Con la cache in `sessionStorage` (ADR 0118) chiudere la scheda chiude l'accesso, e alla scadenza del refresh token,
che Entra limita a 24 ore fisse per una SPA, la dashboard rimanda alla pagina di accesso. Il proprietario chiede un
accesso che duri circa 30 giorni senza reinserire le credenziali. La durata del token non si può allungare: si possono
solo evitare le credenziali finché la sessione Entra è viva.

## Fattori decisionali

- Decisione del proprietario (16/11/2026, intervista del backlog): «localStorage + difese». È lui che supera la 0118.
- MSAL Browser 5 (in uso: `@azure/msal-browser` 5.29.1). Con `cacheLocation: localStorage` la cache è condivisa tra le
  schede. Resta anche dopo la chiusura del browser, ma solo se all'accesso l'utente ha scelto «Rimani connesso» in
  Entra: senza quella scelta la chiave di cifratura sta in un cookie di sessione (documentazione MSAL «Caching»,
  «LocalStorage Notes»). La sessione Entra persistente data da «Rimani connesso» permette un nuovo redirect senza
  credenziali.
- ADR 0118 e rule tech-dashboard: nessun frame nascosto. Il rinnovo silenzioso con iframe richiederebbe `frame-src`
  verso l'IdP e allargherebbe la CSP.
- `.claude/rules/tech-dashboard.md`: MSAL solo in `src/lib/auth.tsx`; nessuna logica di business nella dashboard.
- Direttiva del proprietario (16/11/2026): regole architetturali e componenti riusabili. «Esci» sta nel layout
  condiviso (`src/components/layouts`), non in una pagina.

## Opzioni considerate

1. **Cache in `localStorage` e rinnovo per redirect automatico.**
   - `cacheLocation: BrowserCacheLocation.LocalStorage`.
   - Quando `acquireTokenSilent` fallisce (refresh token scaduto o cache illeggibile), la dashboard avvia da sé
     `acquireTokenRedirect` con lo scope dell'API e `state` uguale alla pagina corrente (solo percorsi della
     dashboard, `returnPathOf`). Lo stesso vale all'apertura senza account in cache.
   - Entra risponde senza credenziali finché la sua sessione è viva; quando la sessione è finita chiede le
     credenziali, come nello scenario «Sessione Entra finita».
   - Una guardia in `sessionStorage` ammette un solo redirect automatico per caricamento. Se il ritorno è un errore
     d'interazione, la pagina di accesso mostra il pulsante «Accedi» invece di rimbalzare all'infinito.
   - «Esci» nel layout chiama `logoutRedirect`, che svuota la cache MSAL e chiude la sessione Entra, con
     `postLogoutRedirectUri` uguale alla radice della dashboard; prima svuota la cache di TanStack Query.
     `localStorage` e `sessionStorage` della dashboard non conservano altro.
2. **Rinnovo silenzioso con iframe (`ssoSilent`)**: scartata, perché è il frame nascosto che la 0118 esclude e
   allarga la CSP.
3. **Backend for frontend con cookie HttpOnly**: scartata per gli stessi motivi della 0118 (servizio nuovo con un
   segreto).
4. **Restare su `sessionStorage` con solo il redirect automatico**: scartata, perché il proprietario ha scelto
   `localStorage`. Anche così ogni nuova scheda farebbe un rimbalzo.

## Esito della decisione

Opzione 1. In `.claude/rules/tech-dashboard.md` §Accesso, nello stesso lavoro, «cache dei token in `sessionStorage`»
diventa `localStorage` con rinnovo per redirect e «Esci», citando questa ADR.

Verifica: prova.
- Unit test di `src/lib/auth.tsx`: cache in `localStorage`; redirect automatico con `state` alla pagina corrente;
  guardia di un solo redirect; `returnPathOf` per i soli percorsi interni; «Esci» che svuota la cache.
- Gli scenari di R6.5.1 nel Task 513.

### Conseguenze

- Uno script nella pagina potrebbe leggere i token: per questo la CSP rigida (Task 512) è parte della stessa User
  Story.
- Dopo la chiusura del browser i token restano solo con «Rimani connesso» scelto in Entra. Senza, il primo caricamento
  fa un redirect senza credenziali finché la sessione Entra è viva. Da verificare su dev: il tenant b736fb4b mostra
  la scelta «Rimani connesso»?
- `postLogoutRedirectUri` è un URI di redirect già registrato (`/dashboard/`) nell'app registration: nessuna modifica
  su Entra.
