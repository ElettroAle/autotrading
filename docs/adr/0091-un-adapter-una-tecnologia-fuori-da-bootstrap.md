# ADR 0091 — Un adapter, una tecnologia fuori da bootstrap: OIDC, esiti degli ordini, tipi precisi

- Stato: accettata (13 novembre 2026)
- Requisiti: Bug B0.0.3 (177)
- Supera: ADR 0048 nella parte che chiama `ReadSourceCommand` il tipo con cui una fonte viene letta
- Collegate: ADR 0089 (un adapter, una tecnologia), ADR 0027 (errori con lo status HTTP), CLAUDE.md (Regola delle
  dipendenze, Nomenclatura)

## Contesto

La ADR 0089 ha reso il test di architettura intransigente e ha elencato in `tests/architecture/known_violations.py`
le violazioni esistenti attribuite al Bug 177. Fuori da `bootstrap.py` erano:

- l'adapter FastAPI importava `jwt` e scaricava la discovery OpenID e le chiavi: due tecnologie in una cartella;
- `adapters/outbound/httpx/position_closing.py` importava `application.orders.outcome`, un modulo di application che
  non è né `ports.py` né `errors.py`;
- 23 moduli di adapter usavano `typing.Any` per le forme JSON e per gli oggetti delle librerie;
- `application/flows/free_capital.py` conteneva `ReadFreeCapitalUseCase` in un modulo che non porta il suo nome;
- `ReadSourceCommand` stava in `application/sources/ports.py`, senza un caso d'uso omonimo nello stesso modulo.

## Decisione

- **La verifica del token Entra è un adapter OIDC** in `adapters/outbound/oidc/` (unica cartella che importa `jwt`),
  dietro due porte di `application/tenancy/ports.py`:
  - `AccessTokenVerifierPort.verify(token) -> VerifiedIdentity`, realizzata da `OidcAccessTokenVerifierAdapter`
    (discovery, chiavi pubbliche con nuovo download quando il `kid` non è noto, solo RS256, issuer, audience, scadenza
    e `oid` obbligatori);
  - `LoginEndpointsPort.endpoints() -> LoginEndpoints`, realizzata da `OidcLoginEndpointsAdapter` (endpoint di
    autorizzazione e di token per la pagina di login di Swagger, letti una volta).
- **La regola del ruolo è del dominio**: `VerifiedIdentity` (in `domain/tenancy`) restituisce l'utente solo se ha il
  ruolo `Utente`, altrimenti `UserRoleMissingError` (403). Gli errori del contratto sono `NotAuthenticatedError` (401)
  e `IdentityProviderUnavailableError` (503) in `application/tenancy/errors.py`. L'adapter FastAPI riceve le due porte
  e chiama solo `verify(token).user()`: le risposte 401/403 restano identiche.
- **`OrderOutcome` è un concetto di dominio**: si sposta da `application/orders/outcome.py` a
  `domain/orders/order_outcome.py`, così l'adapter httpx della chiusura delle posizioni lo importa dal dominio.
- **Niente `typing.Any` negli adapter**: le forme JSON e i documenti delle librerie si descrivono con `TypedDict`,
  `Mapping[str, object]` e `cast` verso il tipo dichiarato dove il dato arriva da una libreria non tipizzata. Le catture
  degli errori di forma già presenti restano, quindi un documento malformato produce lo stesso errore tipizzato di
  prima.
- **`SourceRequest`** sostituisce `ReadSourceCommand`: è il tipo del contratto della porta delle fonti, non il comando di
  un caso d'uso, e resta in `application/sources/ports.py`.
- **`read_free_capital.py`** contiene `ReadFreeCapitalUseCase`; il calcolo del capitale libero di un conto diventa il
  metodo di dominio `FreeCapital.of_account(balance, currency, account_id, flows)`, usato anche da `create_flow` e
  `change_allocated_capital`.

## Alternative scartate

- **Verifica del token dentro l'adapter FastAPI con una porta solo per le chiavi**: la regola dei ruoli e la
  traduzione degli errori di `jwt` resterebbero nella cartella FastAPI, che continuerebbe a importare `jwt`.
- **Adapter OIDC sotto `httpx/`**: il client della discovery è `urllib` della libreria standard; la tecnologia
  caratterizzante è JOSE/OIDC con `jwt`, e mescolarla con httpx violerebbe la stessa regola che si vuole rispettare.
- **`OrderOutcome` esposto in `application/orders/ports.py`**: è il risultato di un ordine sull'exchange, un fatto di
  business che il dominio già usa, non un dettaglio del contratto di una porta.
- **`object` al posto di `Any` senza `TypedDict`**: obbliga a `isinstance` sparsi senza dire quale forma ci si aspetta.

## Conseguenze

- La tabella `TECHNOLOGY_LIBRARIES` dichiara `adapters/outbound/oidc` con `jwt`; il contratto di indipendenza di
  import-linter include la nuova cartella.
- Le voci del Bug 177 fuori da `bootstrap.py` spariscono da `known_violations.py`; restano quelle di `bootstrap.py`.
- Una riga di ciclo con i token solo in parte noti si legge senza costo (prima si leggeva con i token mancanti a
  `None`): le due colonne si scrivono sempre insieme, quindi il caso non nasce dall'applicazione.
