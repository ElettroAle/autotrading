# ADR redirect-dell-accesso-che-non-torna-nei-test — Il redirect dell'accesso non torna nei test della dashboard

- Stato: proposta (17 novembre 2026)
- Requisiti: Bug 549; R6.5.1 (accesso che dura senza nuove credenziali)
- Collegate: ADR 0118 (accesso Entra come SPA con PKCE tramite MSAL)
- Verifica: prova

## Contesto e problema

Il client MSAL dei test della dashboard (`src/testing/test-utils.tsx`) è un `PublicClientApplication` vero. Quando un
test fa partire l'accesso automatico (`startAutomaticSignIn` in `src/lib/auth.tsx`), `acquireTokenRedirect` di MSAL in
jsdom rifiuta in modo asincrono; se il test è già finito, il `catch` gira dopo la chiusura di jsdom e `sessionStorage`
non esiste più. Vitest segnala un "Unhandled Rejection" e il job `quality / test` fallisce anche con tutti i test verdi
(run 44051347570, file `asset-picker.test.tsx`). È intermittente perché dipende da quando arriva il rifiuto.

## Fattori decisionali

- Nel browser un redirect lascia la pagina: la promessa di `acquireTokenRedirect` non si risolve mai. Il finto dei
  test deve comportarsi come il sistema vero, non diversamente.
- Il codice di produzione non si adatta allo smontaggio dei test (`.claude/rules/tests.md`: niente rami di
  produzione per i test).
- I test che provano il rifiuto del redirect (`auth.test.tsx`, `app/index.test.tsx`) lo dichiarano con il proprio
  `vi.spyOn` e restano invariati.

## Decisione

Il client MSAL creato da `test-utils.tsx` per i test ha `acquireTokenRedirect` sostituito da una funzione che
restituisce una promessa che non si risolve mai, come il redirect vero che lascia la pagina. Una prova unitaria di
`test-utils` verifica che la promessa resti in sospeso; la suite completa non deve avere errori non gestiti.

## Alternative scartate

- Controllare `typeof sessionStorage` nel `catch` di `auth.tsx`: codice di produzione scritto per lo smontaggio dei test.
- `dangerouslyIgnoreUnhandledErrors` di Vitest: nasconderebbe errori veri.

## Conseguenze

- Nessun rifiuto asincrono dopo la fine dei test che non lo chiedono; il job fallisce solo per test rossi.
- Un test che vuole il rifiuto del redirect lo dichiara con il proprio spy.
