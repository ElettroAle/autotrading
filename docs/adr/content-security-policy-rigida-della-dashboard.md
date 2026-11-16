# ADR content-security-policy-rigida-della-dashboard — Content Security Policy rigida servita dalla dashboard

- Stato: proposta (16 novembre 2026)
- Requisiti: R6.5.1 (Task 512)
- Collegate: ADR 0117 (container e intestazioni di sicurezza), ADR accesso-persistente-con-cache-msal-in-localstorage

## Contesto e problema

Con i token in `localStorage` (ADR accesso-persistente-con-cache-msal-in-localstorage) uno script estraneo eseguito
nella pagina potrebbe leggerli. Oggi `server/static-server.ts` serve già una CSP: `default-src 'self'`,
`connect-src 'self'` più l'origine dell'issuer, `img-src 'self' data:`, `frame-ancestors 'none'`, `base-uri 'self'`,
`form-action 'self'`. Le direttive per script, stili, oggetti e frame però ricadono solo implicitamente su
`default-src`.

## Fattori decisionali

- Decisione del proprietario (16/11/2026): «localStorage + difese». Lo scenario «Content Security Policy rigida» di
  R6.5.1 chiede script e stili solo dalla propria origine, connessioni solo verso l'API e Entra, niente script inline
  né frame.
- ADR 0117: le intestazioni le serve `server/` (Node, solo libreria standard); nessuna libreria nuova.
- ADR 0118: il browser parla con l'issuer per il codice e il refresh token, quindi `connect-src` deve ammetterlo.

## Opzioni considerate

1. **Direttive esplicite nel server statico.**
   - `default-src 'none'` come base.
   - `script-src 'self'`, `style-src 'self'`, `img-src 'self' data:`, `font-src 'self'`.
   - `connect-src 'self' <origine dell'issuer>`: l'API sta sulla stessa origine, ADR 0117.
   - `manifest-src 'self'`, `frame-src 'none'`, `frame-ancestors 'none'`, `object-src 'none'`.
   - `base-uri 'none'`, `form-action 'self'`.
   - Restano `X-Content-Type-Options: nosniff` e `Referrer-Policy: no-referrer`.
   - Si aggiunge `Strict-Transport-Security`, perché l'installazione è servita solo in HTTPS da Tailscale Serve.

   Una prova verifica che la build di Vite non contenga script né stili inline, che React applichi gli stili via
   CSSOM (ammessi dalla CSP) e che nessuna pagina provochi un evento `securitypolicyviolation`.
2. **Nonce o hash per script inline**: scartata, perché la build non ha script inline e il server statico non
   genera pagine.
3. **`require-trusted-types-for 'script'`**: scartata per ora, perché va verificata con React 19, Recharts e MSAL.
   Se il proprietario la vuole, è un lavoro a sé.

## Esito della decisione

Opzione 1. La rule `tech-dashboard.md` §Container elenca le direttive.

Verifica: prova.
- `server/static-server.test.ts` verifica ogni direttiva e l'assenza di `'unsafe-inline'`.
- Una prova sulla build verifica che `index.html` non abbia `<script>` né `<style>` inline.
- Uno scenario Playwright (Task 513) verifica l'intestazione e che non ci siano violazioni.

### Conseguenze

- Un'aggiunta futura che carica risorse da un'altra origine (font, CDN) fallisce in modo visibile e richiede di
  cambiare questa ADR.
