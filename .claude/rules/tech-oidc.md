---
paths:
  - "src/autotrading/adapters/outbound/oidc/**"
  - "tests/unit/adapters/oidc/**"
---

# Adapter in uscita: identity provider OIDC

- Il sistema integrato è l'identity provider OIDC dell'installazione: oggi Entra ID, sostituibile con qualunque IdP
  OIDC senza cambi nell'app (docs/architecture.md:20). Per questo la cartella porta il nome del protocollo
  dell'identity provider e non del fornitore: l'adapter conosce solo issuer, audience e claim.
- `OidcAccessTokenVerifierAdapter` realizza la verifica del token (R0.1.1): firma con le chiavi JWKS dell'issuer
  (`jwt`, solo RS256), issuer, audience e claim obbligatori (`exp`, `iss`, `aud`, `oid`); restituisce l'`oid` e i ruoli.
  Un token non valido è `NotAuthenticatedError`; un issuer che non risponde o risponde in forma inattesa
  `IdentityProviderUnavailableError`.
- `OidcLoginEndpointsAdapter` legge dal documento di discovery gli endpoint del login Authorization Code + PKCE
  della pagina OpenAPI (ADR 0073); offre solo indirizzi HTTPS.
- Il documento di discovery e le chiavi si leggono solo da indirizzi `https://`, con la libreria standard.
- `composition.py` espone `oidc_adapters(source)`: senza `AUTH_ISSUER` l'installazione non ha ancora il login e
  restituisce `None` (ADR 0016); `configuration.py` la dataclass privata `_OidcSettings`.
